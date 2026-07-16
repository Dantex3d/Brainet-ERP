import sqlite3
conn=sqlite3.connect('db.sqlite3')
cur=conn.cursor()
try:
    cur.execute("SELECT id, name, app, applied FROM django_migrations WHERE app='fees'")
    rows=cur.fetchall()
    for r in rows:
        print(r)
    if not rows:
        print('NO_ROWS')
except Exception as e:
    print('ERR', e)
finally:
    conn.close()
