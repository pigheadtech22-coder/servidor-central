from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db, ConfiguracionSlide

router = APIRouter()

# Modelos Pydantic
class SlideBase(BaseModel):
    nombre: str
    activo: bool
    duracion: int
    orden: int
    parametros: Optional[str] = None

class SlideUpdate(BaseModel):
    activo: Optional[bool] = None
    duracion: Optional[int] = None
    orden: Optional[int] = None
    parametros: Optional[str] = None

class SlideResponse(SlideBase):
    id: int
    clave: str
    fecha_actualizacion: datetime
    
    class Config:
        from_attributes = True

@router.get("/slides", response_model=List[SlideResponse])
async def listar_slides(db: Session = Depends(get_db)):
    """Obtener todos los slides configurados"""
    return db.query(ConfiguracionSlide).order_by(ConfiguracionSlide.orden).all()

@router.get("/slides/secuencia")
async def obtener_secuencia_activa(db: Session = Depends(get_db)):
    """Obtener solo los slides activos en orden para la pantalla pública"""
    slides = db.query(ConfiguracionSlide).filter(
        ConfiguracionSlide.activo == True
    ).order_by(ConfiguracionSlide.orden).all()
    
    return [
        {
            "clave": s.clave,
            "nombre": s.nombre,
            "duracion": s.duracion,
            "parametros": s.parametros
        }
        for s in slides
    ]

@router.put("/slides/{slide_id}", response_model=SlideResponse)
async def actualizar_slide(
    slide_id: int, 
    slide_data: SlideUpdate, 
    db: Session = Depends(get_db)
):
    """Actualizar configuración de un slide"""
    db_slide = db.query(ConfiguracionSlide).filter(ConfiguracionSlide.id == slide_id).first()
    if not db_slide:
        raise HTTPException(status_code=404, detail="Slide no encontrado")
    
    update_data = slide_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_slide, key, value)
    
    db.commit()
    db.refresh(db_slide)
    return db_slide

@router.post("/slides/{slide_id}/toggle")
async def toggle_slide(slide_id: int, db: Session = Depends(get_db)):
    """Activar/Desactivar un slide rápidamente"""
    db_slide = db.query(ConfiguracionSlide).filter(ConfiguracionSlide.id == slide_id).first()
    if not db_slide:
        raise HTTPException(status_code=404, detail="Slide no encontrado")
    
    db_slide.activo = not db_slide.activo
    db.commit()
    return {"id": db_slide.id, "activo": db_slide.activo}
