import sqlite3
import os

db_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "padel_central", "padel_central.db")

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def add_column(table, column, type, default=None):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {type}")
        if default is not None:
             cursor.execute(f"UPDATE {table} SET {column} = ?", (default,))
        print(f"Added column {column} to {table}")
    except sqlite3.OperationalError:
        print(f"Column {column} already exists in {table}")

# Jugadores
add_column("jugadores", "categoria", "TEXT", "6TA")
add_column("jugadores", "ranking_club", "INTEGER", 0)
add_column("jugadores", "ranking_torneo", "INTEGER", 0)

# Torneos
add_column("torneos", "num_sets", "INTEGER", 3)
add_column("torneos", "puntos_set", "INTEGER", 6)
add_column("torneos", "punto_oro", "BOOLEAN", 0)
add_column("torneos", "super_tiebreak_final", "BOOLEAN", 0)
add_column("torneos", "ventajas", "BOOLEAN", 1)

# Partidos
add_column("partidos", "tipo_partido", "TEXT", "libre")

conn.commit()
conn.close()
print("Migration completed.")
