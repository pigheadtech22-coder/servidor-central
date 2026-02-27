from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, date

from ..database import get_db, Torneo, Partido, Jugador, VideoPublicidad, ResultadoSet, ConfiguracionSistema, ConfiguracionSlide
from .marcadores import MarcadorRegistrado

router = APIRouter()
templates = Jinja2Templates(directory="app/static")

def get_config_value(db: Session, clave: str, default: str = "") -> str:
    config = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.clave == clave).first()
    return config.valor if config else default

@router.get("/", response_class=HTMLResponse)
async def dashboard_principal(request: Request, db: Session = Depends(get_db)):
    """Dashboard principal rediseñado como Command Hub"""
    from datetime import timedelta
    modo = get_config_value(db, "modo_sistema", "club")
    
    # 1. Estadísticas Globales
    total_jugadores = db.query(Jugador).filter(Jugador.activo == True).count()
    videos_activos = db.query(VideoPublicidad).filter(VideoPublicidad.activo == True).count()
    
    hoy_min = datetime.combine(date.today(), datetime.min.time())
    hoy_max = datetime.combine(date.today(), datetime.max.time())
    partidos_hoy = db.query(Partido).filter(
        Partido.fecha_programada >= hoy_min,
        Partido.fecha_programada < hoy_max
    ).count()

    # 2. Control de Canchas e Integración de Ecosistema
    # Obtenemos todos los marcadores registrados
    marcadores = db.query(MarcadorRegistrado).order_by(MarcadorRegistrado.cancha_numero).all()
    
    # Mapeamos información en tiempo real para cada cancha (asumiendo 4 canchas por defecto si no hay registros)
    n_canchas = max([m.cancha_numero for m in marcadores] + [4])
    canchas_status = []
    
    for i in range(1, n_canchas + 1):
        marcador = next((m for m in marcadores if m.cancha_numero == i), None)
        status = {"numero": i, "online": False, "marcador": None, "partido": None}
        
        if marcador:
            tiempo_desconectado = datetime.now() - marcador.ultima_conexion
            status["online"] = tiempo_desconectado < timedelta(minutes=10)
            status["marcador"] = marcador
            
        # Buscar partido activo para esta cancha
        partido = db.query(Partido).filter(
            Partido.cancha_numero == i,
            Partido.estado == "en_progreso"
        ).first()
        status["partido"] = partido
        canchas_status.append(status)

    # 3. Datos para "El Cerebro"
    slide_actual = db.query(ConfiguracionSlide).filter(ConfiguracionSlide.activo == True).order_by(ConfiguracionSlide.orden).first()

    # 4. Próximos partidos
    proximos_partidos = db.query(Partido).filter(
        Partido.estado == "programado",
        Partido.fecha_programada >= datetime.now()
    ).order_by(Partido.fecha_programada).limit(5).all()

    # 5. Lista de Jugadores para Selección
    jugadores = db.query(Jugador).filter(Jugador.activo == True).order_by(Jugador.nombre).all()
    jugadores_dict = {j.nombre: j.id for j in jugadores}

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "modo_sistema": modo,
        "total_jugadores": total_jugadores,
        "partidos_hoy": partidos_hoy,
        "videos_activos": videos_activos,
        "canchas": canchas_status,
        "proximos_partidos": proximos_partidos,
        "slide_actual": slide_actual,
        "jugadores": jugadores,
        "jugadores_dict": jugadores_dict
    })

@router.get("/jugadores", response_class=HTMLResponse)
async def dashboard_jugadores(request: Request, db: Session = Depends(get_db)):
    """Dashboard de gestión de jugadores"""
    modo = get_config_value(db, "modo_sistema", "club")
    jugadores = db.query(Jugador).filter(Jugador.activo == True).all()
    
    return templates.TemplateResponse("jugadores.html", {
        "request": request,
        "modo_sistema": modo,
        "jugadores": jugadores
    })

@router.get("/torneos", response_class=HTMLResponse)
async def dashboard_torneos(request: Request, db: Session = Depends(get_db)):
    """Dashboard de gestión de torneos"""
    modo = get_config_value(db, "modo_sistema", "club")
    torneos = db.query(Torneo).filter(Torneo.activo == True).all()
    
    return templates.TemplateResponse("torneos.html", {
        "request": request,
        "modo_sistema": modo,
        "torneos": torneos
    })

@router.get("/partidos", response_class=HTMLResponse)
async def dashboard_partidos(request: Request, db: Session = Depends(get_db)):
    """Dashboard de gestión de partidos"""
    modo = get_config_value(db, "modo_sistema", "club")
    
    partidos_query = db.query(Partido).order_by(Partido.fecha_programada.desc())
    if modo == "torneo":
        partidos_query = partidos_query.filter(Partido.tipo_partido == "torneo")
        
    partidos = partidos_query.limit(50).all()
    
    partidos_enriquecidos = []
    for partido in partidos:
        resultados_sets = db.query(ResultadoSet).filter(
            ResultadoSet.partido_id == partido.id
        ).order_by(ResultadoSet.numero_set).all()
        
        partido_dict = {
            'id': partido.id,
            'torneo_id': partido.torneo_id,
            'tipo_partido': partido.tipo_partido,
            'cancha_numero': partido.cancha_numero,
            'jugador1_id': partido.jugador1_id,
            'jugador2_id': partido.jugador2_id,
            'jugador3_id': partido.jugador3_id,
            'jugador4_id': partido.jugador4_id,
            'estado': partido.estado,
            'fecha_programada': partido.fecha_programada,
            'fecha_inicio': partido.fecha_inicio,
            'fecha_fin': partido.fecha_fin,
            'sets_equipo1': partido.sets_equipo1,
            'sets_equipo2': partido.sets_equipo2,
            'ganador': partido.ganador,
        }
        
        for resultado_set in resultados_sets:
            if resultado_set.numero_set == 1:
                partido_dict['games_set1_equipo1'] = resultado_set.games_equipo1
                partido_dict['games_set1_equipo2'] = resultado_set.games_equipo2
            elif resultado_set.numero_set == 2:
                partido_dict['games_set2_equipo1'] = resultado_set.games_equipo1
                partido_dict['games_set2_equipo2'] = resultado_set.games_equipo2
            elif resultado_set.numero_set == 3:
                partido_dict['games_set3_equipo1'] = resultado_set.games_equipo1
                partido_dict['games_set3_equipo2'] = resultado_set.games_equipo2
        
        partidos_enriquecidos.append(partido_dict)
    
    torneos = db.query(Torneo).filter(Torneo.activo == True).all()
    jugadores = db.query(Jugador).filter(Jugador.activo == True).all()
    
    return templates.TemplateResponse("partidos.html", {
        "request": request,
        "modo_sistema": modo,
        "partidos": partidos_enriquecidos,
        "torneos": torneos,
        "jugadores": jugadores
    })

@router.get("/config/cambiar-modo/{nuevo_modo}")
async def cambiar_modo_sistema(nuevo_modo: str, db: Session = Depends(get_db)):
    """API para cambiar el modo de visualización global (club/torneo)"""
    if nuevo_modo not in ["club", "torneo"]:
        return RedirectResponse(url="/dashboard")
        
    config = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.clave == "modo_sistema").first()
    if config:
        config.valor = nuevo_modo
        db.commit()
    return RedirectResponse(url="/dashboard")

@router.get("/videos", response_class=HTMLResponse)
async def dashboard_videos(request: Request, db: Session = Depends(get_db)):
    """Dashboard de gestión de videos"""
    modo = get_config_value(db, "modo_sistema", "club")
    videos = db.query(VideoPublicidad).order_by(VideoPublicidad.orden).all()
    
    return templates.TemplateResponse("videos.html", {
        "request": request,
        "modo_sistema": modo,
        "videos": videos
    })

@router.get("/horarios", response_class=HTMLResponse)
async def dashboard_horarios(request: Request, db: Session = Depends(get_db)):
    """Dashboard de horarios para pantalla pública"""
    modo = get_config_value(db, "modo_sistema", "club")
    hoy = datetime.combine(date.today(), datetime.min.time())
    
    partidos_query = db.query(Partido).filter(Partido.fecha_programada >= hoy)
    if modo == "torneo":
        partidos_query = partidos_query.filter(Partido.tipo_partido == "torneo")
        
    partidos = partidos_query.order_by(Partido.fecha_programada).limit(20).all()
    
    partidos_data = []
    for partido in partidos:
        jugadores = []
        for jugador_id in [partido.jugador1_id, partido.jugador2_id, partido.jugador3_id, partido.jugador4_id]:
            if jugador_id:
                jugador = db.query(Jugador).filter(Jugador.id == jugador_id).first()
                if jugador:
                    jugadores.append(jugador.nombre)
        
        torneo = db.query(Torneo).filter(Torneo.id == partido.torneo_id).first() if partido.torneo_id else None
        
        partidos_data.append({
            "id": partido.id,
            "cancha": partido.cancha_numero,
            "fecha_programada": partido.fecha_programada,
            "estado": partido.estado,
            "torneo": torneo.nombre if torneo else "Sin torneo",
            "equipo1": f"{jugadores[0]} / {jugadores[1]}" if len(jugadores) >= 2 else "TBD",
            "equipo2": f"{jugadores[2]} / {jugadores[3]}" if len(jugadores) >= 4 else "TBD",
            "resultado": f"{partido.sets_equipo1} - {partido.sets_equipo2}" if partido.estado != "programado" else "-"
        })
    
    return templates.TemplateResponse("horarios.html", {
        "request": request,
        "modo_sistema": modo,
        "partidos": partidos_data,
        "ultima_actualizacion": datetime.now()
    })

@router.get("/gestion-canchas", response_class=HTMLResponse)
async def gestion_canchas(request: Request, db: Session = Depends(get_db)):
    """Dashboard de gestión de canchas y marcadores conectados"""
    from datetime import timedelta
    modo = get_config_value(db, "modo_sistema", "club")
    marcadores = db.query(MarcadorRegistrado).order_by(MarcadorRegistrado.cancha_numero).all()
    
    marcadores_info = []
    for marcador in marcadores:
        tiempo_desconectado = datetime.now() - marcador.ultima_conexion
        estado_conexion = "online" if tiempo_desconectado < timedelta(minutes=10) else "offline"
        
        partido_activo = db.query(Partido).filter(
            and_(
                Partido.cancha_numero == marcador.cancha_numero,
                Partido.estado.in_(["programado", "en_progreso"])
            )
        ).first()
        
        marcadores_info.append({
            "marcador": marcador,
            "estado_conexion": estado_conexion,
            "tiempo_desconectado_minutos": int(tiempo_desconectado.total_seconds() / 60),
            "partido_activo": partido_activo,
            "url_acceso": f"http://{marcador.ip_address}:{marcador.puerto}"
        })
    
    return templates.TemplateResponse("canchas.html", {
        "request": request,
        "modo_sistema": modo,
        "marcadores": marcadores_info,
        "total_marcadores": len(marcadores),
        "marcadores_online": len([m for m in marcadores_info if m["estado_conexion"] == "online"]),
        "canchas_ocupadas": len([m for m in marcadores_info if m["partido_activo"]]),
        "timestamp": datetime.now()
    })

@router.get("/pantallas", response_class=HTMLResponse)
async def gestion_pantallas(request: Request, db: Session = Depends(get_db)):
    """Dashboard de configuración de la pantalla pública (El Cerebro)"""
    from ..database import ConfiguracionSlide
    modo = get_config_value(db, "modo_sistema", "club")
    slides = db.query(ConfiguracionSlide).order_by(ConfiguracionSlide.orden).all()
    
    return templates.TemplateResponse("pantallas.html", {
        "request": request,
        "modo_sistema": modo,
        "slides": slides,
        "total_slides": len(slides),
        "slides_activos": len([s for s in slides if s.activo])
    })
