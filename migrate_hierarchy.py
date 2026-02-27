import sqlite3
import os

db_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "padel_central", "padel_central.db")

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def table_exists(table_name):
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cursor.fetchone() is not None

def add_column(table, column, type, default=None):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {type}")
        if default is not None:
             cursor.execute(f"UPDATE {table} SET {column} = ?", (default,))
        print(f"Added column {column} to {table}")
    except sqlite3.OperationalError:
        print(f"Column {column} already exists in {table}")

# 1. Create missing tables
if not table_exists("categorias"):
    cursor.execute("""
    CREATE TABLE categorias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        torneo_id INTEGER,
        nombre TEXT,
        FOREIGN KEY(torneo_id) REFERENCES torneos(id)
    )
    """)
    print("Created table categorias")

if not table_exists("grupos"):
    cursor.execute("""
    CREATE TABLE grupos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        categoria_id INTEGER,
        nombre TEXT,
        FOREIGN KEY(categoria_id) REFERENCES categorias(id)
    )
    """)
    print("Created table grupos")

if not table_exists("inscritos"):
    cursor.execute("""
    CREATE TABLE inscritos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grupo_id INTEGER,
        jugador1 TEXT,
        jugador2 TEXT,
        categoria TEXT,
        FOREIGN KEY(grupo_id) REFERENCES grupos(id)
    )
    """)
    print("Created table inscritos")

# 2. Add missing columns to partidos
add_column("partidos", "categoria", "TEXT")
add_column("partidos", "hora", "TEXT")
add_column("partidos", "turno", "INTEGER")

conn.commit()
conn.close()
print("Migration completed successfully.")
