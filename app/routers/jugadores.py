from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import os
import shutil
from datetime import datetime

from ..database import get_db, Jugador

router = APIRouter()

# Modelos Pydantic para requests/responses
class JugadorBase(BaseModel):
    nombre: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    categoria: Optional[str] = "6TA"
    ranking_club: Optional[int] = 0
    ranking_torneo: Optional[int] = 0

class JugadorCreate(JugadorBase):
    pass

class JugadorResponse(JugadorBase):
    id: int
    foto: Optional[str]
    partidos_jugados: int
    partidos_ganados: int
    fecha_creacion: datetime
    activo: bool
    
    class Config:
        from_attributes = True

@router.get("/jugadores", response_model=List[JugadorResponse])
async def listar_jugadores(
    skip: int = 0,
    limit: int = 100,
    activos_solo: bool = True,
    db: Session = Depends(get_db)
):
    """Obtener lista de jugadores"""
    query = db.query(Jugador)
    if activos_solo:
        query = query.filter(Jugador.activo == True)
    
    jugadores = query.offset(skip).limit(limit).all()
    return jugadores

@router.get("/jugadores/lista-marcador")
async def obtener_jugadores_para_marcador(
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Obtener jugadores en formato específico para el marcador TV"""
    jugadores = db.query(Jugador).filter(Jugador.activo == True).limit(limit).all()
    
    # Formato exacto que espera el marcador
    resultado = []
    for jugador in jugadores:
        resultado.append({
            "id": jugador.id,
            "nombre": jugador.nombre,
            "foto": jugador.foto or "/jugadores/default.png",
            "categoria": jugador.categoria
        })
    
    return resultado

@router.get("/jugadores/{jugador_id}", response_model=JugadorResponse)
async def obtener_jugador(jugador_id: int, db: Session = Depends(get_db)):
    """Obtener un jugador específico"""
    jugador = db.query(Jugador).filter(Jugador.id == jugador_id).first()
    if not jugador:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    return jugador

@router.post("/jugadores", response_model=JugadorResponse)
async def crear_jugador(jugador: JugadorCreate, db: Session = Depends(get_db)):
    """Crear nuevo jugador"""
    # Verificar que el nombre no existe
    nombre_limpio = jugador.nombre.strip()
    existing = db.query(Jugador).filter(Jugador.nombre == nombre_limpio).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un jugador con este nombre")
    
    db_jugador = Jugador(**jugador.dict())
    db_jugador.nombre = nombre_limpio
    db.add(db_jugador)
    db.commit()
    db.refresh(db_jugador)
    return db_jugador

@router.put("/jugadores/{jugador_id}", response_model=JugadorResponse)
async def actualizar_jugador(
    jugador_id: int, 
    jugador: JugadorBase, 
    db: Session = Depends(get_db)
):
    """Actualizar datos de jugador"""
    db_jugador = db.query(Jugador).filter(Jugador.id == jugador_id).first()
    if not db_jugador:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    
    for key, value in jugador.dict().items():
        if key == "nombre" and value:
            value = value.strip()
        setattr(db_jugador, key, value)
    
    db.commit()
    db.refresh(db_jugador)
    return db_jugador

@router.post("/jugadores/{jugador_id}/foto")
async def subir_foto_jugador(
    jugador_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Subir foto para un jugador"""
    jugador = db.query(Jugador).filter(Jugador.id == jugador_id).first()
    if not jugador:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    
    # Validar tipo de archivo
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")
    
    # Crear nombre único para el archivo
    extension = file.filename.split(".")[-1]
    filename = f"jugador_{jugador_id}_{int(datetime.now().timestamp())}.{extension}"
    file_path = f"uploads/jugadores/{filename}"
    
    # Guardar archivo
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Actualizar jugador con la ruta de la foto
    jugador.foto = f"/uploads/jugadores/{filename}"
    db.commit()
    
    return {"message": "Foto subida correctamente", "foto_url": jugador.foto}

@router.delete("/jugadores/{jugador_id}")
async def eliminar_jugador(jugador_id: int, db: Session = Depends(get_db)):
    """Eliminar (desactivar) un jugador"""
    jugador = db.query(Jugador).filter(Jugador.id == jugador_id).first()
    if not jugador:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    
    jugador.activo = False
    db.commit()
    
    return {"message": "Jugador desactivado correctamente"}

@router.get("/jugadores/buscar/{nombre}")
async def buscar_jugadores(nombre: str, db: Session = Depends(get_db)):
    """Buscar jugadores por nombre"""
    jugadores = db.query(Jugador).filter(
        Jugador.nombre.ilike(f"%{nombre}%"),
        Jugador.activo == True
    ).limit(10).all()
    
    return [
        {
            "id": j.id, 
            "nombre": j.nombre, 
            "foto": j.foto,
            "categoria": j.categoria,
            "ranking_club": j.ranking_club,
            "ranking_torneo": j.ranking_torneo
        } for j in jugadores
    ]
