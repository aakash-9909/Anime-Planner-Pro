import sqlite3
Connection = sqlite3.connect('anime.db')
cursor = Connection.cursor()
cursor.execute("SHOW COLUMNS FROM anime")
ans = cursor.fetchall()
for i in ans:
    print(i)