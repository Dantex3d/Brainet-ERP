import sqlite3
conn=sqlite3.connect('db.sqlite3')
cur=conn.cursor()
try:
    cur.execute('PRAGMA table_info("fees_feeinvoice")')
    rows=cur.fetchall()
    if not rows:
        print('NO_TABLE')
    else:
        for r in rows:
            print(r)
except Exception as e:
    print('ERR', e)
finally:
    conn.close()
