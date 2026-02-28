from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Request, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import shutil
import json
import asyncio
from datetime import datetime
from typing import Set, Dict, Any, List

from .database import get_db, crear_tablas, inicializar_configuraciones
from .routers import jugadores, torneos, partidos, videos, dashboard, canchas, marcadores, pantallas, wizard
from .database import SessionLocal

# Crear la aplicación FastAPI
app = FastAPI(
    title="Servidor Central de Padel",
    description="API para gestión centralizada de torneos de padel",
    version="1.0.0"
)

# --- WebSocket Manager for Real-time Updates ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        # Enviar estado actual al conectar
        await self.send_state_to(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_state_to(self, websocket: WebSocket):
        from .database import SessionLocal
        db = SessionLocal()
        try:
            state = get_master_state(db)
            await websocket.send_text(json.dumps({"type": "update", "data": state}))
        finally:
            db.close()

    async def broadcast_state(self):
        if not self.active_connections: return
        from .database import SessionLocal
        db = SessionLocal()
        try:
            state = get_master_state(db)
            msg = json.dumps({"type": "update", "data": state})
            for connection in self.active_connections:
                try:
                    await connection.send_text(msg)
                except Exception: pass
        finally:
            db.close()

manager = ConnectionManager()

def get_master_state(db: Session):
    from .database import Torneo, Categoria, Grupo, Inscrito, Partido, Jugador
    
    # 1. Torneos y su estructura
    torneos = db.query(Torneo).all()
    torneos_fmt = []
    for t in torneos:
        cats_fmt = []
        for c in t.categorias:
            grps_fmt = []
            for g in c.grupos:
                grps_fmt.append({
                    "id": g.id,
                    "nombre": g.nombre,
                    "inscritos": [
                        {"id": i.id, "j1": i.jugador1, "j2": i.jugador2, "nombre": f"{i.jugador1}{' / ' + i.jugador2 if i.jugador2 else ''}"} 
                        for i in g.inscritos
                    ]
                })
            cats_fmt.append({"id": c.id, "nombre": c.nombre, "grupos": grps_fmt})
        torneos_fmt.append({"id": t.id, "nombre": t.nombre, "tipo": t.tipo_torneo, "categorias": cats_fmt})

    # 2. Próximos partidos (Horarios)
    proximos = db.query(Partido).filter(Partido.estado == "programado").order_by(Partido.fecha_programada.asc()).all()
    prox_fmt = []
    for p in proximos:
        # Obtener nombres de jugadores si hay IDs
        j_nombres = []
        for j_id in [p.jugador1_id, p.jugador2_id, p.jugador3_id, p.jugador4_id]:
            if j_id:
                j = db.query(Jugador).filter(Jugador.id == j_id).first()
                j_nombres.append(j.nombre if j else "TBD")
            else:
                j_nombres.append("TBD")
        
        prox_fmt.append({
            "id": p.id, 
            "hora": p.hora or p.fecha_programada.strftime("%H:%M") if p.fecha_programada else "--:--", 
            "categoria": p.categoria or "Libre",
            "equipo1": f"{j_nombres[0]} / {j_nombres[1]}", 
            "equipo2": f"{j_nombres[2]} / {j_nombres[3]}",
            "estado": p.estado
        })

    # 3. Canchas
    # En el servidor central, las canchas se deducen de los marcadores o partidos activos
    # Para compatibilidad con AdminRemote.jsx asimilamos 4 canchas
    canchas_fmt = []
    for i in range(1, 5):
        p_activo = db.query(Partido).filter(Partido.cancha_numero == i, Partido.estado == "en_progreso").first()
        canchas_fmt.append({"id": i, "ocupada": p_activo is not None, "partido_id": p_activo.id if p_activo else None})

    return {
        "tier": "PRO", # El servidor central soporta todo
        "torneos": torneos_fmt,
        "horarios": prox_fmt,
        "canchas": canchas_fmt
    }

# Configurar CORS para permitir peticiones desde el marcador
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server port 1
        "http://localhost:5174",  # Vite dev server port 2  
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "*"  # En producción, cambiar por IPs específicas
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Crear tablas al inicio
crear_tablas()

# Inicializar configuraciones por defecto
@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    try:
        inicializar_configuraciones(db)
    finally:
        db.close()

# Configurar archivos estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Configurar templates
templates = Jinja2Templates(directory="app/static")

# Incluir routers
app.include_router(jugadores.router, prefix="/api/v1", tags=["jugadores"])
app.include_router(torneos.router, prefix="/api/v1", tags=["torneos"])
app.include_router(partidos.router, prefix="/api/v1", tags=["partidos"])
app.include_router(videos.router, prefix="/api/v1", tags=["videos"])
app.include_router(marcadores.router, prefix="/api/v1/marcadores", tags=["marcadores"])
app.include_router(pantallas.router, prefix="/api/v1/pantallas", tags=["pantallas"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(canchas.router, prefix="/canchas", tags=["canchas"])
app.include_router(wizard.router, prefix="/api", tags=["wizard"])

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        manager.disconnect(websocket)

@app.get("/api/data")
async def get_all_data(db: Session = Depends(get_db)):
    return get_master_state(db)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Página principal del dashboard"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Endpoint para verificar que el servidor está funcionando"""
    return {
        "status": "ok", 
        "timestamp": datetime.now(),
        "service": "Servidor Central Padel"
    }

# Endpoint especial para las Raspberry Pi
@app.get("/api/cancha/{cancha_numero}/estado")
async def estado_cancha(cancha_numero: int, db: Session = Depends(get_db)):
    """Obtener el estado actual de una cancha específica para las Raspberry Pi"""
    from .database import Partido, Jugador
    from sqlalchemy import and_
    
    # Buscar partido activo en esta cancha priorizando en_progreso
    partido_activo = db.query(Partido).filter(
        and_(
            Partido.cancha_numero == cancha_numero,
            Partido.estado == "en_progreso"
        )
    ).order_by(Partido.fecha_inicio.desc(), Partido.id.desc()).first()

    # Si no hay partido en progreso, usar el próximo programado
    if not partido_activo:
        partido_activo = db.query(Partido).filter(
            and_(
                Partido.cancha_numero == cancha_numero,
                Partido.estado == "programado"
            )
        ).order_by(Partido.fecha_programada.asc(), Partido.id.asc()).first()
    
    if not partido_activo:
        return {
            "cancha": cancha_numero,
            "estado": "libre",
            "partido": None
        }
    
    # Obtener datos de jugadores
    jugadores_data = {}
    for i, jugador_id in enumerate([
        partido_activo.jugador1_id,
        partido_activo.jugador2_id, 
        partido_activo.jugador3_id,
        partido_activo.jugador4_id
    ], 1):
        if jugador_id:
            jugador = db.query(Jugador).filter(Jugador.id == jugador_id).first()
            if jugador:
                jugadores_data[f"jugador{i}"] = {
                    "id": jugador.id,
                    "nombre": jugador.nombre,
                    "foto": jugador.foto
                }
    
    # Obtener resultados por set
    from .database import ResultadoSet
    resultados_sets = db.query(ResultadoSet).filter(
        ResultadoSet.partido_id == partido_activo.id
    ).order_by(ResultadoSet.numero_set).all()

    sets_detalle = [
        {
            "numero_set": r.numero_set,
            "games_equipo1": r.games_equipo1,
            "games_equipo2": r.games_equipo2,
            "ganador_set": r.ganador_set,
            "finalizado": r.finalizado
        }
        for r in resultados_sets
    ]

    # Arrays planos [set1, set2, set3] para el marcador
    equipo1_games = [r.games_equipo1 for r in resultados_sets] + [0] * (3 - len(resultados_sets))
    equipo2_games = [r.games_equipo2 for r in resultados_sets] + [0] * (3 - len(resultados_sets))

    return {
        "cancha": cancha_numero,
        "estado": "ocupada",
        "partido": {
            "id": partido_activo.id,
            "torneo_id": partido_activo.torneo_id,
            "estado": partido_activo.estado,
            "fecha_programada": partido_activo.fecha_programada,
            "jugadores": jugadores_data,
            "sets_equipo1": partido_activo.sets_equipo1,
            "sets_equipo2": partido_activo.sets_equipo2,
            "equipo1_games": equipo1_games,
            "equipo2_games": equipo2_games,
            "sets_detalle": sets_detalle
        }
    }

@app.post("/api/cancha/{cancha_numero}/resultado")
async def actualizar_resultado(
    cancha_numero: int,
    resultado: dict,
    db: Session = Depends(get_db)
):
    """
    Recibir resultado de partido desde el marcador (Raspberry Pi).

    Formatos aceptados:
      1. Arrays de games por set:
         { "equipo1_games": [6, 3, 0], "equipo2_games": [4, 6, 0] }
         Los arrays tienen 3 posiciones (un valor por set).
      2. Formato legacy con sets totales:
         { "sets_equipo1": 2, "sets_equipo2": 1 }
    """
    from .database import Partido, ResultadoSet
    from sqlalchemy import and_

    partido = db.query(Partido).filter(
        and_(
            Partido.cancha_numero == cancha_numero,
            Partido.estado.in_(["programado", "en_progreso"])
        )
    ).first()

    if not partido:
        raise HTTPException(status_code=404, detail="No hay partido activo en esta cancha")

    partido.estado = "en_progreso"
    if not partido.fecha_inicio:
        partido.fecha_inicio = datetime.now()

    # --- Formato arrays [games_set1, games_set2, games_set3] ---
    equipo1_games = resultado.get("equipo1_games") or resultado.get("equipo1") or []
    equipo2_games = resultado.get("equipo2_games") or resultado.get("equipo2") or []

    if equipo1_games and equipo2_games:
        sets_ganados_e1 = 0
        sets_ganados_e2 = 0

        for i, (g1, g2) in enumerate(zip(equipo1_games, equipo2_games)):
            numero_set = i + 1

            # Un set es válido si al menos uno de los dos tiene puntos
            if g1 == 0 and g2 == 0 and i > 0:
                continue

            set_terminado = (g1 >= 6 or g2 >= 6) and abs(g1 - g2) >= 2
            ganador_set = None
            if set_terminado:
                ganador_set = "equipo1" if g1 > g2 else "equipo2"
                if ganador_set == "equipo1":
                    sets_ganados_e1 += 1
                else:
                    sets_ganados_e2 += 1

            resultado_set = db.query(ResultadoSet).filter(
                ResultadoSet.partido_id == partido.id,
                ResultadoSet.numero_set == numero_set
            ).first()

            if resultado_set:
                resultado_set.games_equipo1 = g1
                resultado_set.games_equipo2 = g2
                resultado_set.ganador_set = ganador_set
                resultado_set.finalizado = set_terminado
            else:
                db.add(ResultadoSet(
                    partido_id=partido.id,
                    numero_set=numero_set,
                    games_equipo1=g1,
                    games_equipo2=g2,
                    ganador_set=ganador_set,
                    finalizado=set_terminado
                ))

        partido.sets_equipo1 = sets_ganados_e1
        partido.sets_equipo2 = sets_ganados_e2
    else:
        # Formato legacy
        if "sets_equipo1" in resultado:
            partido.sets_equipo1 = resultado["sets_equipo1"]
        if "sets_equipo2" in resultado:
            partido.sets_equipo2 = resultado["sets_equipo2"]

    # Finalizar partido si hay ganador (mejor de 3 sets = 2 ganados)
    if partido.sets_equipo1 >= 2 or partido.sets_equipo2 >= 2:
        partido.estado = "finalizado"
        partido.fecha_fin = datetime.now()
        partido.ganador = "equipo1" if partido.sets_equipo1 > partido.sets_equipo2 else "equipo2"

    db.commit()

    from .database import manager
    import asyncio
    asyncio.create_task(manager.broadcast_state())

    return {
        "message": "Resultado actualizado correctamente",
        "sets_equipo1": partido.sets_equipo1,
        "sets_equipo2": partido.sets_equipo2,
        "estado": partido.estado
    }


@app.get("/api/cancha/{cancha_numero}/stream")
async def stream_cancha(cancha_numero: int):
    """
    Server-Sent Events (SSE) para recibir actualizaciones en tiempo real de una cancha.
    El cliente se conecta y recibe un evento 'estado' cada 2 segundos con los datos actuales.

    Uso en JavaScript:
        const es = new EventSource('/api/cancha/1/stream');
        es.addEventListener('estado', e => {
            const data = JSON.parse(e.data);
            console.log(data);
        });
    """
    async def event_generator():
        while True:
            db = SessionLocal()
            try:
                from .database import Partido, Jugador, ResultadoSet
                from sqlalchemy import and_

                partido_activo = db.query(Partido).filter(
                    and_(
                        Partido.cancha_numero == cancha_numero,
                        Partido.estado.in_(["programado", "en_progreso"])
                    )
                ).first()

                if not partido_activo:
                    payload = {"cancha": cancha_numero, "estado": "libre", "partido": None}
                else:
                    resultados_sets = db.query(ResultadoSet).filter(
                        ResultadoSet.partido_id == partido_activo.id
                    ).order_by(ResultadoSet.numero_set).all()

                    equipo1_games = [r.games_equipo1 for r in resultados_sets] + [0] * (3 - len(resultados_sets))
                    equipo2_games = [r.games_equipo2 for r in resultados_sets] + [0] * (3 - len(resultados_sets))

                    payload = {
                        "cancha": cancha_numero,
                        "estado": "ocupada",
                        "partido": {
                            "id": partido_activo.id,
                            "estado": partido_activo.estado,
                            "sets_equipo1": partido_activo.sets_equipo1,
                            "sets_equipo2": partido_activo.sets_equipo2,
                            "equipo1_games": equipo1_games,
                            "equipo2_games": equipo2_games,
                            "num_sets": partido_activo.num_sets,
                            "punto_oro": partido_activo.punto_oro
                        }
                    }
            finally:
                db.close()

            yield f"event: estado\ndata: {json.dumps(payload)}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True
    )