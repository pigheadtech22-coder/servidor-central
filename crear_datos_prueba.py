#!/usr/bin/env python3
"""
Script para inicializar datos de prueba en el servidor central
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal, Jugador, Torneo, Partido
from datetime import datetime, timedelta
import random

def crear_datos_prueba():
    db = SessionLocal()
    
    try:
        print("🏓 Inicializando datos de prueba para el servidor central...")
        
        # Crear jugadores de prueba
        jugadores_data = [
            {"nombre": "Carlos Martín", "email": "carlos.martin@email.com", "telefono": "611234567"},
            {"nombre": "Ana García", "email": "ana.garcia@email.com", "telefono": "622345678"},
            {"nombre": "Diego López", "email": "diego.lopez@email.com", "telefono": "633456789"},
            {"nombre": "María Ruiz", "email": "maria.ruiz@email.com", "telefono": "644567890"},
            {"nombre": "Javier Sánchez", "email": "javier.sanchez@email.com", "telefono": "655678901"},
            {"nombre": "Carmen Jiménez", "email": "carmen.jimenez@email.com", "telefono": "666789012"},
            {"nombre": "Roberto Silva", "email": "roberto.silva@email.com", "telefono": "677890123"},
            {"nombre": "Elena Moreno", "email": "elena.moreno@email.com", "telefono": "688901234"},
            {"nombre": "Pedro Castillo", "email": "pedro.castillo@email.com", "telefono": "699012345"},
            {"nombre": "Lucía Herrera", "email": "lucia.herrera@email.com", "telefono": "600123456"},
            {"nombre": "Manuel Torres", "email": "manuel.torres@email.com", "telefono": "611234568"},
            {"nombre": "Isabel Vargas", "email": "isabel.vargas@email.com", "telefono": "622345679"}
        ]
        
        jugadores = []
        for data in jugadores_data:
            # Verificar si ya existe
            existente = db.query(Jugador).filter(Jugador.email == data["email"]).first()
            if not existente:
                jugador = Jugador(**data)
                db.add(jugador)
                db.commit()
                db.refresh(jugador)
                jugadores.append(jugador)
                print(f"  ✅ Jugador creado: {jugador.nombre}")
            else:
                jugadores.append(existente)
                print(f"  ℹ️  Jugador ya existía: {existente.nombre}")
        
        # Crear torneo de prueba
        torneo_existente = db.query(Torneo).filter(Torneo.nombre == "Torneo de Prueba").first()
        if not torneo_existente:
            torneo = Torneo(
                nombre="Torneo de Prueba",
                descripcion="Torneo para probar el sistema",
                fecha_inicio=datetime.now(),
                fecha_fin=datetime.now() + timedelta(days=2),
                tipo_torneo="eliminacion_directa",
                num_canchas=6,
                activo=True
            )
            db.add(torneo)
            db.commit()
            db.refresh(torneo)
            print(f"  ✅ Torneo creado: {torneo.nombre}")
        else:
            torneo = torneo_existente
            print(f"  ℹ️  Torneo ya existía: {torneo.nombre}")
        
        # Crear partidos de prueba
        partidos_prueba = [
            {
                "jugadores": [0, 1, 2, 3],  # Índices en la lista de jugadores
                "cancha": 1,
                "estado": "en_progreso",
                "sets": (1, 2),
                "programado": datetime.now() - timedelta(hours=1)
            },
            {
                "jugadores": [4, 5, 6, 7],
                "cancha": 2,
                "estado": "en_progreso", 
                "sets": (2, 0),
                "programado": datetime.now() - timedelta(minutes=30)
            },
            {
                "jugadores": [8, 9, 10, 11],
                "cancha": 3,
                "estado": "programado",
                "sets": (0, 0),
                "programado": datetime.now() + timedelta(minutes=15)
            }
        ]
        
        for i, partido_data in enumerate(partidos_prueba):
            # Verificar si ya existe un partido en esa cancha
            existente = db.query(Partido).filter(
                Partido.cancha_numero == partido_data["cancha"],
                Partido.estado.in_(["programado", "en_progreso"])
            ).first()
            
            if not existente:
                partido = Partido(
                    torneo_id=torneo.id,
                    jugador1_id=jugadores[partido_data["jugadores"][0]].id,
                    jugador2_id=jugadores[partido_data["jugadores"][1]].id,
                    jugador3_id=jugadores[partido_data["jugadores"][2]].id,
                    jugador4_id=jugadores[partido_data["jugadores"][3]].id,
                    cancha_numero=partido_data["cancha"],
                    estado=partido_data["estado"],
                    fecha_programada=partido_data["programado"],
                    sets_equipo1=partido_data["sets"][0],
                    sets_equipo2=partido_data["sets"][1]
                )
                
                if partido_data["estado"] == "en_progreso":
                    partido.fecha_inicio = partido_data["programado"]
                
                db.add(partido)
                db.commit()
                db.refresh(partido)
                
                jugador1 = jugadores[partido_data["jugadores"][0]].nombre
                jugador2 = jugadores[partido_data["jugadores"][1]].nombre
                jugador3 = jugadores[partido_data["jugadores"][2]].nombre
                jugador4 = jugadores[partido_data["jugadores"][3]].nombre
                
                print(f"  ✅ Partido creado en cancha {partido_data['cancha']}: "
                      f"{jugador1}/{jugador2} vs {jugador3}/{jugador4} "
                      f"({partido_data['sets'][0]}-{partido_data['sets'][1]})")
            else:
                print(f"  ℹ️  Ya existe partido activo en cancha {partido_data['cancha']}")
        
        print("\n🎉 ¡Datos de prueba inicializados correctamente!")
        print(f"📊 Total de jugadores: {len(jugadores)}")
        print(f"🏆 Total de torneos: 1")
        print(f"⚔️  Total de partidos activos: {len(partidos_prueba)}")
        
        print("\n🔗 URLs disponibles:")
        print("  👀 Estado de canchas: http://localhost:8000/canchas/estado")
        print("  📊 Dashboard: http://localhost:8000/dashboard")
        print("  🎯 API Estado canchas: http://localhost:8000/canchas/api/estado-completo")
        print("  📋 Panel horarios: http://localhost:8000/static/horarios.html")
        
    except Exception as e:
        print(f"❌ Error al crear datos de prueba: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    crear_datos_prueba()