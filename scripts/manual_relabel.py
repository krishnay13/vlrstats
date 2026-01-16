import sqlite3

DB='valorant_esports.db'
updates=[
    (498631,'Gen.G',None),
    (490310,'Gen.G',None),
    (458826,'Gen.G','Global Esports'),
    (508828,'Gen.G','Global Esports'),
]

def main():
    conn=sqlite3.connect(DB)
    cur=conn.cursor()
    for mid,ta,tb in updates:
        row=cur.execute('select team_a, team_b from Matches where match_id=?',(mid,)).fetchone()
        print('before',mid,row)
        if row is None:
            continue
        new_ta=row[0] if ta is None else ta
        new_tb=row[1] if tb is None else tb
        cur.execute('update Matches set team_a=?, team_b=? where match_id=?',(new_ta,new_tb,mid))
        if ta is not None:
            cur.execute('update Player_Stats set team=? where match_id=? and team=?',(new_ta,mid,row[0]))
        if tb is not None:
            cur.execute('update Player_Stats set team=? where match_id=? and team=?',(new_tb,mid,row[1]))
        row2=cur.execute('select team_a, team_b from Matches where match_id=?',(mid,)).fetchone()
        print('after ',mid,row2)
    conn.commit(); conn.close()

if __name__=='__main__':
    main()
