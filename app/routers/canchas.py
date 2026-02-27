from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

from ..database import get_db, Partido, Jugador, Torneo

router = APIRouter()
templates = Jinja2Templates(directory="app/static")

@router.get("/estado", response_class=HTMLResponse)
async def ver_estado_canchas(request: Request, db: Session = Depends(get_db)):
    """Vista del estado de todas las canchas para displays públicos"""
    
    # Obtener información de todas las canchas (1 a 6)
    canchas = []
    
    for numero_cancha in range(1, 7):  # Canchas 1 al 6
        # Buscar partido activo en esta cancha
        partido_activo = db.query(Partido).filter(
            and_(
                Partido.cancha_numero == numero_cancha,
                Partido.estado.in_(["programado", "en_progreso"])
            )
        ).first()
        
        cancha_info = {
            "numero": numero_cancha,
            "estado": "libre",
            "partido": None
        }
        
        if partido_activo:
            # Obtener información del torneo
            torneo = db.query(Torneo).filter(Torneo.id == partido_activo.torneo_id).first()
            
            # Obtener nombres de jugadores
            jugadores = []
            for jugador_id in [
                partido_activo.jugador1_id,
                partido_activo.jugador2_id, 
                partido_activo.jugador3_id,
                partido_activo.jugador4_id
            ]:
                if jugador_id:
                    jugador = db.query(Jugador).filter(Jugador.id == jugador_id).first()
                    if jugador:
                        jugadores.append(jugador.nombre)
            
            # Construir resultado actual
            resultado_texto = "0 - 0"
            if partido_activo.sets_equipo1 is not None and partido_activo.sets_equipo2 is not None:
                resultado_texto = f"{partido_activo.sets_equipo1} - {partido_activo.sets_equipo2}"
            
            cancha_info = {
                "numero": numero_cancha,
                "estado": "ocupada",
                "partido": {
                    "id": partido_activo.id,
                    "torneo": torneo.nombre if torneo else "Torneo sin nombre",
                    "jugadores": jugadores,
                    "resultado": resultado_texto,
                    "estado": partido_activo.estado,
                    "fecha_programada": partido_activo.fecha_programada,
                    "sets_equipo1": partido_activo.sets_equipo1 or 0,
                    "sets_equipo2": partido_activo.sets_equipo2 or 0
                }
            }
        
        canchas.append(cancha_info)
    
    return templates.TemplateResponse(
        "canchas.html", 
        {
            "request": request,
            "canchas": canchas,
            "timestamp": datetime.now()
        }
    )

@router.get("/api/estado-completo")
async def obtener_estado_completo(db: Session = Depends(get_db)):
    """API endpoint para obtener estado completo de todas las canchas (para uso AJAX)"""
    
    canchas = []
    
    for numero_cancha in range(1, 7):
        # Buscar partido activo en esta cancha
        partido_activo = db.query(Partido).filter(
            and_(
                Partido.cancha_numero == numero_cancha,
                Partido.estado.in_(["programado", "en_progreso"])
            )
        ).first()
        
        cancha_info = {
            "numero": numero_cancha,
            "estado": "libre",
            "partido": None
        }
        
        if partido_activo:
            # Obtener información del torneo
            torneo = db.query(Torneo).filter(Torneo.id == partido_activo.torneo_id).first()
            
            # Obtener jugadores con información completa
            jugadores_data = []
            for jugador_id in [
                partido_activo.jugador1_id,
                partido_activo.jugador2_id, 
                partido_activo.jugador3_id,
                partido_activo.jugador4_id
            ]:
                if jugador_id:
                    jugador = db.query(Jugador).filter(Jugador.id == jugador_id).first()
                    if jugador:
                        jugadores_data.append({
                            "id": jugador.id,
                            "nombre": jugador.nombre,
                            "foto": jugador.foto
                        })
            
            cancha_info = {
                "numero": numero_cancha,
                "estado": "ocupada",
                "partido": {
                    "id": partido_activo.id,
                    "torneo_id": partido_activo.torneo_id,
                    "torneo_nombre": torneo.nombre if torneo else "Torneo sin nombre",
                    "jugadores": jugadores_data,
                    "estado": partido_activo.estado,
                    "fecha_programada": partido_activo.fecha_programada.isoformat() if partido_activo.fecha_programada else None,
                    "fecha_inicio": partido_activo.fecha_inicio.isoformat() if partido_activo.fecha_inicio else None,
                    "sets_equipo1": partido_activo.sets_equipo1 or 0,
                    "sets_equipo2": partido_activo.sets_equipo2 or 0,
                    "resultado_actual": f"{partido_activo.sets_equipo1 or 0} - {partido_activo.sets_equipo2 or 0}"
                }
            }
        
        canchas.append(cancha_info)
    
    # Estadísticas generales
    total_canchas = len(canchas)
    canchas_libres = len([c for c in canchas if c["estado"] == "libre"])
    canchas_ocupadas = total_canchas - canchas_libres
    
    return {
        "canchas": canchas,
        "estadisticas": {
            "total": total_canchas,
            "libres": canchas_libres,
            "ocupadas": canchas_ocupadas,
            "timestamp": datetime.now().isoformat()
        }
    }

@router.post("/api/{cancha_numero}/iniciar-partido")
async def iniciar_partido_cancha(
    cancha_numero: int,
    partido_id: int,
    db: Session = Depends(get_db)
):
    """Iniciar un partido específico en una cancha"""
    
    # Verificar que la cancha esté libre
    partido_existente = db.query(Partido).filter(
        and_(
            Partido.cancha_numero == cancha_numero,
            Partido.estado.in_(["programado", "en_progreso"])
        )
    ).first()
    
    if partido_existente and partido_existente.id != partido_id:
        raise HTTPException(
            status_code=400, 
            detail=f"La cancha {cancha_numero} ya tiene un partido activo"
        )
    
    # Obtener el partido a iniciar
    partido = db.query(Partido).filter(Partido.id == partido_id).first()
    if not partido:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    
    # Asignar cancha e iniciar partido
    partido.cancha_numero = cancha_numero
    partido.estado = "en_progreso"
    partido.fecha_inicio = datetime.now()
    
    db.commit()
    db.refresh(partido)
    
    return {
        "message": f"Partido iniciado en cancha {cancha_numero}",
        "partido": {
            "id": partido.id,
            "cancha": cancha_numero,
            "estado": partido.estado,
            "fecha_inicio": partido.fecha_inicio
        }
    }

@router.post("/api/{cancha_numero}/liberar")
async def liberar_cancha(cancha_numero: int, db: Session = Depends(get_db)):
    """Liberar una cancha (finalizar partido actual)"""
    
    partido_activo = db.query(Partido).filter(
        and_(
            Partido.cancha_numero == cancha_numero,
            Partido.estado.in_(["programado", "en_progreso"])
        )
    ).first()
    
    if not partido_activo:
        raise HTTPException(
            status_code=404, 
            detail=f"No hay partido activo en la cancha {cancha_numero}"
        )
    
    # Finalizar partido
    partido_activo.estado = "finalizado"
    partido_activo.fecha_fin = datetime.now()
    
    db.commit()
    
    return {
        "message": f"Cancha {cancha_numero} liberada",
        "partido_finalizado": partido_activo.id
    }