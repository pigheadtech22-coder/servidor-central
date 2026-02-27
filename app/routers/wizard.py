from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from ..database import get_db, Torneo, Categoria, Grupo, Inscrito, Partido, Jugador
from .partidos import PartidoResponse

router = APIRouter()

class WizardCreate(BaseModel):
    nombre: str
    tipo: str # grupos_elim, elim_directa, round_robin
    categoria: str
    num_grupos: int = 4

class InscritoCreate(BaseModel):
    grupo_id: int
    j1: str
    j2: Optional[str] = None
    categoria: Optional[str] = None

class PartidoWizardCreate(BaseModel):
    hora: str
    categoria: str
    torneo_id: int
    e1_j1: str
    e1_j2: Optional[str] = ""
    e2_j1: str
    e2_j2: Optional[str] = ""

@router.post("/wizard/create")
async def wizard_create(data: WizardCreate, db: Session = Depends(get_db)):
    """Crear estructura de torneo (Wizard)"""
    # Crear torneo
    db_torneo = Torneo(nombre=data.nombre, tipo_torneo=data.tipo)
    db.add(db_torneo)
    db.flush() # Obtener ID

    # Crear categoria
    db_cat = Categoria(torneo_id=db_torneo.id, nombre=data.categoria)
    db.add(db_cat)
    db.flush()

    # Crear grupos
    for i in range(1, data.num_grupos + 1):
        nombre_grupo = f"Grupo {chr(64 + i)}" if i <= 26 else f"Grupo {i}"
        db_grupo = Grupo(categoria_id=db_cat.id, nombre=nombre_grupo)
        db.add(db_grupo)

    db.commit()
    
    # Broadcast update
    from ..main import manager
    import asyncio
    asyncio.create_task(manager.broadcast_state())
    
    return {"status": "ok", "torneo_id": db_torneo.id}

@router.post("/inscritos")
async def add_inscrito(data: InscritoCreate, db: Session = Depends(get_db)):
    """Inscribir pareja en un grupo"""
    nuevo = Inscrito(
        grupo_id=data.grupo_id,
        jugador1=data.j1,
        jugador2=data.j2,
        categoria=data.categoria
    )
    db.add(nuevo)
    db.commit()
    
    from ..main import manager
    import asyncio
    asyncio.create_task(manager.broadcast_state())
    
    return {"status": "ok"}

@router.delete("/inscritos/{inscrito_id}")
async def delete_inscrito(inscrito_id: int, db: Session = Depends(get_db)):
    """Eliminar inscripción"""
    db.query(Inscrito).filter(Inscrito.id == inscrito_id).delete()
    db.commit()
    
    from ..main import manager
    import asyncio
    asyncio.create_task(manager.broadcast_state())
    
    return {"status": "ok"}

@router.post("/partido")
async def crear_partido_wizard(data: PartidoWizardCreate, db: Session = Depends(get_db)):
    """Añadir partido desde el manager (Wizard/AdminRemote)"""
    
    # Intentar encontrar IDs de jugadores por nombre (para compatibilidad con sistema de rankings central)
    def buscar_jugador(nombre):
        if not nombre or nombre.upper() == "TBD": 
            return None
        from sqlalchemy import func
        clean_name = nombre.strip().lower()
        j = db.query(Jugador).filter(func.lower(func.trim(Jugador.nombre)) == clean_name).first()
        if j:
            print(f"✅ Jugador encontrado: '{nombre}' -> ID {j.id}")
            return j.id
        print(f"⚠️ Jugador NO encontrado: '{nombre}' (buscado como: '{clean_name}')")
        return None

    id1 = buscar_jugador(data.e1_j1)
    id2 = buscar_jugador(data.e1_j2)
    id3 = buscar_jugador(data.e2_j1)
    id4 = buscar_jugador(data.e2_j2)

    p = Partido(
        hora=data.hora,
        categoria=data.categoria,
        torneo_id=data.torneo_id,
        jugador1_id=id1,
        jugador2_id=id2,
        jugador3_id=id3,
        jugador4_id=id4,
        tipo_partido="torneo",
        estado="programado"
    )
    
    # Si no encontramos IDs, guardamos nombres en algun campo? 
    # Por ahora el sistema central requiere IDs. 
    # TODO: Crear jugadores automáticamente si no existen?
    
    db.add(p)
    db.commit()
    
    from ..main import manager
    import asyncio
    asyncio.create_task(manager.broadcast_state())
    
    return {"status": "ok", "id": p.id}
