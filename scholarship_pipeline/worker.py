import os
import signal
import subprocess
import time
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(".env.vm")

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL must be set in .env.vm")

engine = create_engine(DB_URL)


def kill_process_tree(pid):
    """Kill a process and all its children (Chrome tabs etc)."""
    try:
        import psutil
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            try:
                child.kill()
            except Exception:
                pass
        parent.kill()
    except Exception:
        # Fallback: kill process group
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except Exception:
            pass


def is_job_cancelled(job_id):
    """Check if a job has been set to CANCELLED in the DB."""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT status FROM scrape_jobs WHERE id = :id"),
                {"id": job_id}
            ).fetchone()
            return result and result[0] == "CANCELLED"
    except Exception:
        return False


def recover_stale_jobs():
    """
    On startup, reset any jobs that were left as RUNNING (orphaned from a
    crashed or disconnected worker session) back to PENDING so they get retried.
    A job is considered stale if it has been RUNNING for more than 5 minutes
    and has no recorded completion time.
    """
    with engine.connect() as conn:
        result = conn.execute(text("""
            UPDATE scrape_jobs
            SET status = 'PENDING', started_at = NULL
            WHERE status = 'RUNNING'
              AND started_at < NOW() - INTERVAL '5 minutes'
            RETURNING id
        """))
        recovered = result.fetchall()
        conn.commit()

    if recovered:
        for (job_id,) in recovered:
            print(f"[{datetime.now().isoformat()}] ♻️  Recovered orphaned job: {job_id} → reset to PENDING")
    else:
        print(f"[{datetime.now().isoformat()}] No orphaned jobs found.")


def run_worker():
    print(f"[{datetime.now().isoformat()}] Worker starting, waiting for jobs...")
    recover_stale_jobs()
    while True:
        try:
            with engine.connect() as conn:
                # 1. Find a PENDING job
                result = conn.execute(text(
                    "SELECT id, source_id, job_type FROM scrape_jobs "
                    "WHERE status = 'PENDING' ORDER BY created_at ASC LIMIT 1"
                )).fetchone()

                if not result:
                    time.sleep(10)
                    continue

                job_id, source_id, job_type = result
                print(f"[{datetime.now().isoformat()}] Found pending job: {job_id} for source {source_id}")

                # 2. Mark as RUNNING
                conn.execute(text(
                    "UPDATE scrape_jobs SET status = 'RUNNING', started_at = NOW(), "
                    "current_step = 'Pipeline starting', progress_percent = 5 WHERE id = :id"
                ), {"id": job_id})
                conn.commit()

                # 3. Execute the pipeline
                print(f"[{datetime.now().isoformat()}] Executing pipeline for source {source_id}...")

                cmd = ["venv/bin/python", "main.py", "--source-id", str(source_id)]

                log_file = f"output/logs/job_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
                os.makedirs(os.path.dirname(log_file), exist_ok=True)

                print(f"[{datetime.now().isoformat()}] Streaming logs to {log_file}")

                # Step → progress % mapping from main.py log output
                STEP_PROGRESS = {
                    "step 0": 5,  "loading sources": 5,
                    "step 1": 10, "discover": 15,
                    "step 2": 25, "classif": 30,
                    "step 3": 40, "crawl": 45,
                    "[fetch]": 50, "[scrape]": 52,  # crawl4ai per-page lines
                    "step 4": 55, "resolve": 58,
                    "step 5": 60, "extract": 70,
                    "step 6": 85, "dedup": 87,
                    "step 7": 90, "saving": 92,
                    "step 8": 95, "save to database": 95,
                }

                cancelled = False

                with open(log_file, "w", encoding="utf-8") as f:
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        start_new_session=True  # puts process in its own group for clean kill
                    )

                    full_log = []
                    last_progress_update = time.time()
                    last_cancel_check = time.time()

                    for line in process.stdout:
                        print(line, end="")
                        f.write(line)
                        f.flush()
                        full_log.append(line)

                        now = time.time()

                        # Check for cancellation every 10 seconds
                        if now - last_cancel_check > 10:
                            last_cancel_check = now
                            if is_job_cancelled(job_id):
                                print(f"[{datetime.now().isoformat()}] Job {job_id} cancelled — killing subprocess")
                                kill_process_tree(process.pid)
                                cancelled = True
                                break

                        # Update progress every 5s based on log keywords
                        if now - last_progress_update > 5:
                            line_lower = line.lower()
                            for keyword, pct in STEP_PROGRESS.items():
                                if keyword in line_lower:
                                    try:
                                        with engine.connect() as progress_conn:
                                            progress_conn.execute(text(
                                                "UPDATE scrape_jobs SET progress_percent = :pct, "
                                                "current_step = :step WHERE id = :id"
                                            ), {"pct": pct, "step": line.strip()[:120], "id": job_id})
                                            progress_conn.commit()
                                    except Exception:
                                        pass
                                    last_progress_update = now
                                    break

                    process.wait()

                # 4. Handle results
                if cancelled:
                    print(f"[{datetime.now().isoformat()}] Job {job_id} was cancelled.")
                    conn.execute(text(
                        "UPDATE scrape_jobs SET status = 'CANCELLED', completed_at = NOW(), "
                        "current_step = 'Cancelled by user' WHERE id = :id"
                    ), {"id": job_id})
                elif process.returncode == 0:
                    print(f"[{datetime.now().isoformat()}] Job {job_id} completed successfully.")
                    conn.execute(text(
                        "UPDATE scrape_jobs SET status = 'COMPLETED', completed_at = NOW(), "
                        "progress_percent = 100 WHERE id = :id"
                    ), {"id": job_id})
                else:
                    print(f"[{datetime.now().isoformat()}] Job {job_id} FAILED.")
                    error_log = "".join(full_log)[-2000:] if full_log else "Unknown error"
                    conn.execute(text(
                        "UPDATE scrape_jobs SET status = 'FAILED', completed_at = NOW(), error_log = :error WHERE id = :id"
                    ), {"id": job_id, "error": error_log})

                conn.commit()

        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Worker error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_worker()
