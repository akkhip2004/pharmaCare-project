import sqlite3

print("Creating database...")

conn = sqlite3.connect("database.db")

# 🗄️ Medicine Table
conn.execute('''
CREATE TABLE IF NOT EXISTS medicine (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    batch TEXT,
    expiry DATE,
    location TEXT
)
''')

# 🔐 Users Table (NEW)
conn.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
''')

print("Database and tables created successfully!")

conn.close()