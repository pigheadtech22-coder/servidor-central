from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db, Torneo, Partido, Jugador

router = APIRouter()

# Modelos Pydantic
class TorneoBase(BaseModel):
    nombre: str
    fecha_inicio: datetime
    fecha_fin: Optional[datetime] = None
    descripcion: Optional[str] = None
    num_canchas: int = 1
    tipo_torneo: str = "eliminacion"
    
    # Configuración de reglas
    num_sets: int = 3
    puntos_set: int = 6
    punto_oro: bool = False
    super_tiebreak_final: bool = False
    ventajas: bool = True
    
    reglas_especiales: Optional[str] = None

class TorneoCreate(TorneoBase):
    pass

class TorneoResponse(TorneoBase):
    id: int
    activo: bool
    finalizado: bool
    
    class Config:
        from_attributes = True

@router.get("/torneos", response_model=List[TorneoResponse])
async def listar_torneos(
    skip: int = 0,
    limit: int = 100,
    activos_solo: bool = True,
    db: Session = Depends(get_db)
):
    """Obtener lista de torneos"""
    query = db.query(Torneo)
    if activos_solo:
        query = query.filter(Torneo.activo == True)
    
    torneos = query.offset(skip).limit(limit).all()
    return torneos

@router.get("/torneos/{torneo_id}", response_model=TorneoResponse)
async def obtener_torneo(torneo_id: int, db: Session = Depends(get_db)):
    """Obtener un torneo específico"""
    torneo = db.query(Torneo).filter(Torneo.id == torneo_id).first()
    if not torneo:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    return torneo

@router.post("/torneos", response_model=TorneoResponse)
async def crear_torneo(torneo: TorneoCreate, db: Session = Depends(get_db)):
    """Crear nuevo torneo"""
    db_torneo = Torneo(**torneo.dict())
    db.add(db_torneo)
    db.commit()
    db.refresh(db_torneo)
    return db_torneo

@router.get("/torneos/{torneo_id}/partidos")
async def obtener_partidos_torneo(torneo_id: int, db: Session = Depends(get_db)):
    """Obtener todos los partidos de un torneo"""
    torneo = db.query(Torneo).filter(Torneo.id == torneo_id).first()
    if not torneo:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    
    partidos = db.query(Partido).filter(Partido.torneo_id == torneo_id).all()
    
    result = []
    for partido in partidos:
        # Obtener datos de jugadores
        jugadores = {}
        for i, jugador_id in enumerate([
            partido.jugador1_id, partido.jugador2_id,
            partido.jugador3_id, partido.jugador4_id
        ], 1):
            if jugador_id:
                jugador = db.query(Jugador).filter(Jugador.id == jugador_id).first()
                if jugador:
                    jugadores[f"jugador{i}"] = {
                        "id": jugador.id,
                        "nombre": jugador.nombre,
                        "foto": jugador.foto,
                        "categoria": jugador.categoria
                    }
        
        result.append({
            "id": partido.id,
            "cancha_numero": partido.cancha_numero,
            "estado": partido.estado,
            "fecha_programada": partido.fecha_programada,
            "fecha_inicio": partido.fecha_inicio,
            "fecha_fin": partido.fecha_fin,
            "sets_equipo1": partido.sets_equipo1,
            "sets_equipo2": partido.sets_equipo2,
            "ganador": partido.ganador,
            "jugadores": jugadores
        })
    
    return result

@router.get("/torneos/{torneo_id}/cuadro")
async def obtener_cuadro_torneo(torneo_id: int, db: Session = Depends(get_db)):
    """Obtener el cuadro/bracket del torneo"""
    torneo = db.query(Torneo).filter(Torneo.id == torneo_id).first()
    if not torneo:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    
    partidos = db.query(Partido).filter(Partido.torneo_id == torneo_id).all()
    
    # Organizar partidos por ronda/fase
    cuadro = {
        "torneo": {
            "id": torneo.id,
            "nombre": torneo.nombre,
            "tipo": torneo.tipo_torneo,
            "reglas": {
                "num_sets": torneo.num_sets,
                "puntos_set": torneo.puntos_set,
                "punto_oro": torneo.punto_oro,
                "super_tiebreak": torneo.super_tiebreak_final,
                "ventajas": torneo.ventajas
            }
        },
        "partidos_por_estado": {
            "programados": [],
            "en_progreso": [],
            "finalizados": []
        }
    }
    
    for partido in partidos:
        partido_data = {
            "id": partido.id,
            "cancha": partido.cancha_numero,
            "fecha_programada": partido.fecha_programada,
            "sets_equipo1": partido.sets_equipo1,
            "sets_equipo2": partido.sets_equipo2,
            "ganador": partido.ganador
        }
        
        cuadro["partidos_por_estado"][partido.estado].append(partido_data)
    
    return cuadro

@router.put("/torneos/{torneo_id}/finalizar")
async def finalizar_torneo(torneo_id: int, db: Session = Depends(get_db)):
    """Marcar torneo como finalizado"""
    torneo = db.query(Torneo).filter(Torneo.id == torneo_id).first()
    if not torneo:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    
    torneo.finalizado = True
    torneo.fecha_fin = datetime.now()
    db.commit()
    
    return {"message": "Torneo finalizado correctamente"}
