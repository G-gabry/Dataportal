import sqlite3
import os

db = 'progress.db'
if not os.path.exists(db):
    print('No progress.db found. No runs yet.')
else:
    conn = sqlite3.connect(db)
    
    # Check what tables exist
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print("Tables:", tables)
    
    # Get all runs with stats
    try:
        rows = conn.execute("""
            SELECT r.run_id, r.started_at, COALESCE(r.finished_at, 'RUNNING'),
                   COUNT(DISTINCT CASE WHEN u.crawl_status = 'done' THEN u.url END),
                   COUNT(DISTINCT CASE WHEN i.id IS NOT NULL THEN i.id END)
            FROM runs r
            LEFT JOIN urls u ON r.run_id = u.run_id
            LEFT JOIN items i ON r.run_id = i.run_id
            GROUP BY r.run_id
            ORDER BY r.started_at DESC
        """).fetchall()
    except Exception:
        rows = conn.execute("SELECT run_id, started_at, finished_at FROM runs ORDER BY started_at DESC").fetchall()
    
    print("\n{:<22} {:<22} {:<12}".format("Run ID", "Started", "Status"))
    print("-" * 70)
    for row in rows:
        print("{:<22} {:<22} {:<12}".format(str(row[0]), str(row[1])[:20], str(row[2])[:12]))
    
    conn.close()
