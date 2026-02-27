#!/usr/bin/env python3
"""
Script para migrar jugadores del marcador local al servidor central
"""

import sys
import os
import json
import re
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal, Jugador

def generar_email_desde_nombre(nombre):
    """Generar un email único basado en el nombre del jugador"""
    # Limpiar el nombre: quitar espacios, convertir a minúsculas, quitar caracteres especiales
    nombre_limpio = re.sub(r'[^a-zA-Z0-9\s]', '', nombre.lower())
    nombre_limpio = re.sub(r'\s+', '.', nombre_limpio.strip())
    
    # Generar email
    email = f"{nombre_limpio}@padel.local"
    return email

def migrar_jugadores_locales():
    """Migrar jugadores desde el JSON local al servidor central"""
    
    # Ruta al archivo de jugadores local
    archivo_jugadores = r"c:\Users\pighe\OneDrive\Documentos\diseno aplicaciones\marcador tv\src\data\jugadores.json"
    
    try:
        # Leer jugadores del archivo local
        with open(archivo_jugadores, 'r', encoding='utf-8') as f:
            jugadores_locales = json.load(f)
        
        print(f"📂 Encontrados {len(jugadores_locales)} jugadores en el archivo local")
        
        # Conectar a la base de datos del servidor central
        db = SessionLocal()
        
        try:
            jugadores_migrados = 0
            jugadores_actualizados = 0
            
            for jugador_local in jugadores_locales:
                nombre = jugador_local.get('nombre', '').strip()
                if not nombre:
                    continue

                # Generar email único
                email = generar_email_desde_nombre(nombre)
                
                # Verificar si ya existe (por nombre o email)
                existente = db.query(Jugador).filter(
                    (Jugador.nombre == nombre) | 
                    (Jugador.email == email)
                ).first()
                
                if not existente:
                    # Crear nuevo jugador en servidor central
                    nuevo_jugador = Jugador(
                        nombre=nombre,
                        email=email,
                        telefono=None,  # No tenemos teléfono en el local
                        foto=jugador_local.get('foto')  # Mantener la ruta de la foto
                    )
                    
                    db.add(nuevo_jugador)
                    db.commit()
                    db.refresh(nuevo_jugador)
                    
                    print(f"  ✅ Migrado: {nuevo_jugador.nombre} (ID: {nuevo_jugador.id})")
                    jugadores_migrados += 1
                    
                else:
                    # Actualizar foto si no la tiene
                    if not existente.foto and jugador_local.get('foto'):
                        existente.foto = jugador_local.get('foto')
                        db.commit()
                        print(f"  🔄 Actualizada foto: {existente.nombre}")
                        jugadores_actualizados += 1
                    else:
                        print(f"  ℹ️  Ya existe: {existente.nombre}")
            
            print(f"\n🎉 Migración completada:")
            print(f"  📈 Jugadores migrados: {jugadores_migrados}")
            print(f"  🔄 Jugadores actualizados: {jugadores_actualizados}")
            print(f"  📊 Total en servidor central: {db.query(Jugador).count()}")
            
            # Mostrar algunos ejemplos
            print(f"\n📋 Primeros 5 jugadores en servidor central:")
            primeros = db.query(Jugador).limit(5).all()
            for j in primeros:
                print(f"  - {j.nombre} ({j.email}) | Foto: {j.foto or 'Sin foto'}")
            
        except Exception as e:
            print(f"❌ Error durante la migración: {e}")
            db.rollback()
        finally:
            db.close()
            
    except FileNotFoundError:
        print(f"❌ No se encontró el archivo: {archivo_jugadores}")
    except json.JSONDecodeError as e:
        print(f"❌ Error al leer JSON: {e}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

def listar_jugadores_servidor_central():
    """Listar todos los jugadores del servidor central"""
    db = SessionLocal()
    try:
        jugadores = db.query(Jugador).all()
        print(f"\n👥 Jugadores en servidor central ({len(jugadores)}):")
        print("=" * 60)
        
        for jugador in jugadores:
            foto_info = f"📸 {jugador.foto}" if jugador.foto else "🚫 Sin foto"
            print(f"ID: {jugador.id:3d} | {jugador.nombre:25s} | {foto_info}")
            
    except Exception as e:
        print(f"❌ Error al listar jugadores: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrar jugadores del marcador local al servidor central')
    parser.add_argument('--migrar', action='store_true', help='Ejecutar migración')
    parser.add_argument('--listar', action='store_true', help='Listar jugadores actuales')
    
    args = parser.parse_args()
    
    if args.migrar:
        print("🔄 Iniciando migración de jugadores...")
        migrar_jugadores_locales()
    elif args.listar:
        listar_jugadores_servidor_central()
    else:
        print("📋 Opciones disponibles:")
        print("  python migrar_jugadores.py --migrar    # Migrar jugadores")
        print("  python migrar_jugadores.py --listar    # Listar jugadores")
        print("\n🎯 Ejecutando migración por defecto...")
        migrar_jugadores_locales()