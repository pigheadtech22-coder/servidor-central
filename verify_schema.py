import sqlite3
import os

db_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "padel_central", "padel_central.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables = ["categorias", "grupos", "inscritos"]
for table in tables:
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
    exists = cursor.fetchone()
    if exists:
        print(f"Table '{table}' exists.")
        cursor.execute(f"PRAGMA table_info({table})")
        cols = cursor.fetchall()
        for col in cols:
            print(f"  Column: {col[1]} ({col[2]})")
    else:
        print(f"Table '{table}' DOES NOT exist.")

# Check Partido columns
cursor.execute("PRAGMA table_info(partidos)")
cols = cursor.fetchall()
partido_cols = [c[1] for c in cols]
msg = "Column {col} exists in partidos."
for col in ["categoria", "hora", "turno"]:
    if col in partido_cols:
        print(msg.format(col=col))
    else:
        print(f"Column {col} MISSING in partidos.")

conn.close()
