import sqlite3
import os

db = 'progress.db'
if not os.path.exists(db):
    print('No progress.db found. No runs yet.')
else:
    conn = sqlite3.connect(db)
    
    rows = conn.execute("""
        SELECT 
            r.run_id, 
            r.started_at,
            CASE WHEN r.finished_at IS NULL THEN 'RUNNING' ELSE 'DONE' END as status,
            COALESCE(m.total_discovered, 0) as discovered,
            COALESCE(m.total_crawled, 0) as crawled,
            COALESCE(m.total_extracted, 0) as extracted,
            COALESCE(m.total_final, 0) as final
        FROM runs r
        LEFT JOIN run_meta m ON r.run_id = m.run_id
        ORDER BY r.started_at DESC
    """).fetchall()

    header = "{:<22} {:<21} {:<9} {:>10} {:>8} {:>10} {:>7}".format(
        "Run ID", "Started", "Status", "Discovered", "Crawled", "Extracted", "Final"
    )
    print(header)
    print("-" * 90)
    for row in rows:
        print("{:<22} {:<21} {:<9} {:>10} {:>8} {:>10} {:>7}".format(
            str(row[0]), str(row[1])[:20], str(row[2]),
            row[3], row[4], row[5], row[6]
        ))

    conn.close()
