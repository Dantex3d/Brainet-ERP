import sqlite3
conn=sqlite3.connect('db.sqlite3')
cur=conn.cursor()
try:
    tables=['fees_feepayment','fees_feeinvoice','fees_studentfeeaccount','fees_feestructure','fees_feeledger']
    for t in tables:
        try:
            cur.execute(f"DROP TABLE IF EXISTS {t}")
            print('DROPPED', t)
        except Exception as e:
            print('ERR_DROP', t, e)
    conn.commit()
except Exception as e:
    print('ERR', e)
finally:
    conn.close()
