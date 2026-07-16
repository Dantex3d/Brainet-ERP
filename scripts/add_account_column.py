import shutil, sqlite3
shutil.copy('db.sqlite3', 'db.sqlite3.backup')
conn=sqlite3.connect('db.sqlite3')
cur=conn.cursor()
try:
    cur.execute("ALTER TABLE fees_feeinvoice ADD COLUMN account_id bigint")
    conn.commit()
    print('ADDED')
except Exception as e:
    print('ERR', e)
finally:
    conn.close()
