from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db, Partido, Torneo, Jugador, ResultadoSet

router = APIRouter()

# Modelos Pydantic
class PartidoCreate(BaseModel):
    torneo_id: Optional[int] = None
    cancha_numero: int
    tipo_partido: str = "club"  # torneo, liga, club, libre
    jugador1_id: int
    jugador2_id: int
    jugador3_id: int
    jugador4_id: int
    fecha_programada: datetime
    num_sets: Optional[int] = 3
    punto_oro: Optional[bool] = False

class PartidoResponse(BaseModel):
    id: int
    torneo_id: Optional[int]
    cancha_numero: int
    tipo_partido: str
    estado: str
    fecha_programada: datetime
    fecha_inicio: Optional[datetime]
    fecha_fin: Optional[datetime]
    sets_equipo1: int
    sets_equipo2: int
    ganador: Optional[str]
    num_sets: int
    punto_oro: bool
    
    class Config:
        from_attributes = True

class ActualizarResultado(BaseModel):
    sets_equipo1: int
    sets_equipo2: int
    resultados_sets: List[dict]

@router.get("/partidos")
async def listar_partidos(
    torneo_id: Optional[int] = None,
    cancha_numero: Optional[int] = None,
    estado: Optional[str] = None,
    tipo_partido: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Obtener lista de partidos con filtros opcionales"""
    query = db.query(Partido)
    
    if torneo_id:
        query = query.filter(Partido.torneo_id == torneo_id)
    if cancha_numero:
        query = query.filter(Partido.cancha_numero == cancha_numero)
    if estado:
        query = query.filter(Partido.estado == estado)
    if tipo_partido:
        query = query.filter(Partido.tipo_partido == tipo_partido)
    
    partidos = query.all()
    
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
        
        # Obtener torneo
        torneo = db.query(Torneo).filter(Torneo.id == partido.torneo_id).first() if partido.torneo_id else None
        
        result.append({
            "id": partido.id,
            "torneo": {"id": torneo.id, "nombre": torneo.nombre} if torneo else None,
            "tipo_partido": partido.tipo_partido,
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

@router.get("/partidos/{partido_id}")
async def obtener_partido(partido_id: int, db: Session = Depends(get_db)):
    """Obtener detalles completos de un partido"""
    partido = db.query(Partido).filter(Partido.id == partido_id).first()
    if not partido:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    
    # Obtener jugadores
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
    
    # Obtener resultados de sets
    resultados_sets = db.query(ResultadoSet).filter(
        ResultadoSet.partido_id == partido_id
    ).order_by(ResultadoSet.numero_set).all()
    
    sets_detalle = []
    for resultado in resultados_sets:
        sets_detalle.append({
            "numero_set": resultado.numero_set,
            "games_equipo1": resultado.games_equipo1,
            "games_equipo2": resultado.games_equipo2,
            "ganador_set": resultado.ganador_set,
            "finalizado": resultado.finalizado
        })
    
    # Obtener torneo
    torneo = db.query(Torneo).filter(Torneo.id == partido.torneo_id).first() if partido.torneo_id else None
    
    return {
        "id": partido.id,
        "torneo": {"id": torneo.id, "nombre": torneo.nombre} if torneo else None,
        "tipo_partido": partido.tipo_partido,
        "cancha_numero": partido.cancha_numero,
        "estado": partido.estado,
        "fecha_programada": partido.fecha_programada,
        "fecha_inicio": partido.fecha_inicio,
        "fecha_fin": partido.fecha_fin,
        "sets_equipo1": partido.sets_equipo1,
        "sets_equipo2": partido.sets_equipo2,
        "ganador": partido.ganador,
        "jugadores": jugadores,
        "sets_detalle": sets_detalle
    }

@router.post("/partidos", response_model=PartidoResponse)
async def crear_partido(partido: PartidoCreate, db: Session = Depends(get_db)):
    """Crear nuevo partido"""
    if partido.torneo_id:
        torneo = db.query(Torneo).filter(Torneo.id == partido.torneo_id).first()
        if not torneo:
            raise HTTPException(status_code=404, detail="Torneo no encontrado")
    
    # Verificar que todos los jugadores existen
    jugadores_ids = [
        partido.jugador1_id, partido.jugador2_id, 
        partido.jugador3_id, partido.jugador4_id
    ]
    
    for jugador_id in jugadores_ids:
        if jugador_id:
            jugador = db.query(Jugador).filter(Jugador.id == jugador_id).first()
            if not jugador:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Jugador con ID {jugador_id} no encontrado"
                )
    
    # Verificar que no hay conflicto de horario/cancha
    conflicto = db.query(Partido).filter(
        Partido.cancha_numero == partido.cancha_numero,
        Partido.fecha_programada == partido.fecha_programada,
        Partido.estado.in_(["programado", "en_progreso"])
    ).first()
    
    if conflicto:
        raise HTTPException(
            status_code=400, 
            detail="Ya hay un partido programado en esa cancha a esa hora"
        )
    
    db_partido = Partido(**partido.dict())
    db.add(db_partido)
    db.commit()
    db.refresh(db_partido)
    
    from ..main import manager
    import asyncio
    asyncio.create_task(manager.broadcast_state())
    
    return db_partido

def actualizar_rankings(db: Session, partido: Partido):
    """Lógica para actualizar victorias y rankings de jugadores"""
    equipo1_ids = [partido.jugador1_id, partido.jugador2_id]
    equipo2_ids = [partido.jugador3_id, partido.jugador4_id]
    
    ganadores_ids = equipo1_ids if partido.ganador == "equipo1" else equipo2_ids
    todos_ids = equipo1_ids + equipo2_ids
    
    for jugador_id in todos_ids:
        if not jugador_id: continue
        jugador = db.query(Jugador).filter(Jugador.id == jugador_id).first()
        if not jugador: continue
        
        jugador.partidos_jugados += 1
        es_ganador = jugador_id in ganadores_ids
        
        if es_ganador:
            jugador.partidos_ganados += 1
            # Subir ranking según tipo de partido
            if partido.tipo_partido == "torneo":
                jugador.ranking_torneo += 10
            elif partido.tipo_partido in ["club", "liga"]:
                jugador.ranking_club += 5
        else:
            # Bajar un poco si pierde (opcional, por ahora solo sumamos)
            pass

@router.put("/partidos/{partido_id}/resultado")
async def actualizar_resultado_partido(
    partido_id: int, 
    resultado: ActualizarResultado,
    db: Session = Depends(get_db)
):
    """Actualizar resultado de un partido y actualizar rankings si finaliza"""
    partido = db.query(Partido).filter(Partido.id == partido_id).first()
    if not partido:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    
    # Si ya estaba finalizado, no procesamos rankings de nuevo
    ya_finalizado = (partido.estado == "finalizado")

    # Actualizar resultado general
    partido.sets_equipo1 = resultado.sets_equipo1
    partido.sets_equipo2 = resultado.sets_equipo2
    
    # Determinar ganador y estado
    if resultado.sets_equipo1 >= 2 or resultado.sets_equipo2 >= 2:
        partido.estado = "finalizado"
        partido.fecha_fin = datetime.now()
        partido.ganador = "equipo1" if resultado.sets_equipo1 > resultado.sets_equipo2 else "equipo2"
        
        # Actualizar rankings si es la primera vez que finaliza
        if not ya_finalizado:
            actualizar_rankings(db, partido)
    else:
        partido.estado = "en_progreso"
        if not partido.fecha_inicio:
            partido.fecha_inicio = datetime.now()
    
    # Actualizar resultados de sets
    for set_data in resultado.resultados_sets:
        resultado_set = db.query(ResultadoSet).filter(
            ResultadoSet.partido_id == partido_id,
            ResultadoSet.numero_set == set_data["numero_set"]
        ).first()
        
        if resultado_set:
            resultado_set.games_equipo1 = set_data["games_equipo1"]
            resultado_set.games_equipo2 = set_data["games_equipo2"]
            resultado_set.ganador_set = "equipo1" if set_data["games_equipo1"] > set_data["games_equipo2"] else "equipo2"
            resultado_set.finalizado = set_data.get("finalizado", True)
        else:
            nuevo_resultado_set = ResultadoSet(
                partido_id=partido_id,
                numero_set=set_data["numero_set"],
                games_equipo1=set_data["games_equipo1"],
                games_equipo2=set_data["games_equipo2"],
                ganador_set="equipo1" if set_data["games_equipo1"] > set_data["games_equipo2"] else "equipo2",
                finalizado=set_data.get("finalizado", True)
            )
            db.add(nuevo_resultado_set)
    
    db.commit()
    
    from ..main import manager
    import asyncio
    asyncio.create_task(manager.broadcast_state())
    
    return {"message": "Resultado actualizado correctamente"}

@router.put("/partidos/{partido_id}/estado")
async def cambiar_estado_partido(
    partido_id: int,
    nuevo_estado: str,
    db: Session = Depends(get_db)
):
    """Cambiar estado de un partido"""
    valid_estados = ["programado", "en_progreso", "finalizado", "cancelado"]
    if nuevo_estado not in valid_estados:
        raise HTTPException(
            status_code=400, 
            detail=f"Estado inválido. Debe ser uno de: {valid_estados}"
        )
    
    partido = db.query(Partido).filter(Partido.id == partido_id).first()
    if not partido:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    
    partido.estado = nuevo_estado
    
    if nuevo_estado == "en_progreso" and not partido.fecha_inicio:
        partido.fecha_inicio = datetime.now()
    elif nuevo_estado == "finalizado" and not partido.fecha_fin:
        partido.fecha_fin = datetime.now()
    
    db.commit()
    
    from ..main import manager
    import asyncio
    asyncio.create_task(manager.broadcast_state())
    
    return {"message": f"Estado cambiado a {nuevo_estado}"}

@router.get("/canchas/{cancha_numero}/estado")
async def estado_cancha_actual(cancha_numero: int, db: Session = Depends(get_db)):
    """Obtener estado actual de una cancha (para Raspberry Pi)"""
    from sqlalchemy import and_
    
    partido_activo = db.query(Partido).filter(
        and_(
            Partido.cancha_numero == cancha_numero,
            Partido.estado.in_(["programado", "en_progreso"])
        )
    ).first()
    
    if not partido_activo:
        return {"cancha": cancha_numero, "estado": "libre", "partido": None}
    
    jugadores_data = {}
    for i, jugador_id in enumerate([
        partido_activo.jugador1_id, partido_activo.jugador2_id,
        partido_activo.jugador3_id, partido_activo.jugador4_id
    ], 1):
        if jugador_id:
            jugador = db.query(Jugador).filter(Jugador.id == jugador_id).first()
            if jugador:
                jugadores_data[f"jugador{i}"] = {
                    "id": jugador.id,
                    "nombre": jugador.nombre,
                    "foto": jugador.foto,
                    "categoria": jugador.categoria
                }
    
    return {
        "cancha": cancha_numero,
        "estado": "ocupada",
        "partido": {
            "id": partido_activo.id,
            "torneo_id": partido_activo.torneo_id,
            "tipo_partido": partido_activo.tipo_partido,
            "estado": partido_activo.estado,
            "fecha_programada": partido_activo.fecha_programada,
            "jugadores": jugadores_data,
            "sets_equipo1": partido_activo.sets_equipo1,
            "sets_equipo2": partido_activo.sets_equipo2
        }
    }
