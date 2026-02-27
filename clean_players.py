import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.database import SessionLocal, Jugador

def clean_database():
    db = SessionLocal()
    try:
        jugadores = db.query(Jugador).all()
        print(f"🔍 Revisando {len(jugadores)} jugadores...")
        
        count = 0
        for j in jugadores:
            changed = False
            
            if j.nombre != j.nombre.strip():
                print(f"  ✨ Limpiando nombre: '{j.nombre}' -> '{j.nombre.strip()}'")
                j.nombre = j.nombre.strip()
                changed = True
            
            if j.email and j.email != j.email.strip():
                print(f"  ✨ Limpiando email: '{j.email}' -> '{j.email.strip()}'")
                j.email = j.email.strip()
                changed = True
                
            if changed:
                count += 1
        
        if count > 0:
            db.commit()
            print(f"\n✅ Total de jugadores corregidos: {count}")
        else:
            print("\n✅ No se encontraron nombres con espacios innecesarios.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clean_database()
