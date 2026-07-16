import sqlite3
conn=sqlite3.connect('db.sqlite3')
cur=conn.cursor()
try:
    cur.execute("SELECT COUNT(1) FROM django_migrations WHERE app='fees' AND name='0001_initial'")
    row=cur.fetchone()
    print('FOUND', row[0])
    cur.execute("DELETE FROM django_migrations WHERE app='fees' AND name='0001_initial'")
    conn.commit()
    print('DELETED')
except Exception as e:
    print('ERR', e)
finally:
    conn.close()
