from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
import os
import shutil
from datetime import datetime

from ..database import get_db, VideoPublicidad

router = APIRouter()

# Modelos Pydantic
class VideoResponse(BaseModel):
    id: int
    nombre: str
    archivo: str
    duracion: float
    activo: bool
    orden: int
    fecha_subida: datetime
    
    class Config:
        from_attributes = True

class ActualizarOrdenVideo(BaseModel):
    videos_orden: List[dict]  # [{"id": 1, "orden": 1}, {"id": 2, "orden": 2}]

@router.get("/videos", response_model=List[VideoResponse])
async def listar_videos(
    activos_solo: bool = True,
    db: Session = Depends(get_db)
):
    """Obtener lista de videos de publicidad"""
    query = db.query(VideoPublicidad)
    if activos_solo:
        query = query.filter(VideoPublicidad.activo == True)
    
    videos = query.order_by(VideoPublicidad.orden).all()
    return videos

@router.get("/videos/{video_id}", response_model=VideoResponse)
async def obtener_video(video_id: int, db: Session = Depends(get_db)):
    """Obtener un video específico"""
    video = db.query(VideoPublicidad).filter(VideoPublicidad.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video no encontrado")
    return video

@router.post("/videos/upload", response_model=VideoResponse)
async def subir_video(
    file: UploadFile = File(...),
    nombre: str = None,
    db: Session = Depends(get_db)
):
    """Subir nuevo video de publicidad"""
    
    # Validar tipo de archivo
    valid_types = ["video/mp4", "video/webm", "video/ogg", "video/avi", "video/mov"]
    if file.content_type not in valid_types:
        raise HTTPException(
            status_code=400, 
            detail="Formato de video no soportado. Use MP4, WebM, OGG, AVI o MOV"
        )
    
    # Crear nombre único para el archivo
    timestamp = int(datetime.now().timestamp())
    extension = file.filename.split(".")[-1]
    filename = f"video_{timestamp}.{extension}"
    file_path = f"uploads/videos/{filename}"
    
    # Guardar archivo
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Obtener siguiente orden disponible
    max_orden = db.query(VideoPublicidad).count()
    
    # Crear registro en base de datos
    db_video = VideoPublicidad(
        nombre=nombre or file.filename,
        archivo=f"/uploads/videos/{filename}",
        orden=max_orden + 1,
        activo=True
    )
    
    # TODO: Obtener duración real del video usando ffmpeg o similar
    # Por ahora usar estimado
    file_size = os.path.getsize(file_path)
    estimated_duration = file_size / (1024 * 1024 * 2)  # Estimado: ~2MB por minuto
    db_video.duracion = estimated_duration
    
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    
    return db_video

@router.delete("/videos/{video_id}")
async def eliminar_video(video_id: int, db: Session = Depends(get_db)):
    """Eliminar video de publicidad"""
    video = db.query(VideoPublicidad).filter(VideoPublicidad.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video no encontrado")
    
    # Eliminar archivo físico
    if video.archivo and os.path.exists(video.archivo.lstrip('/')):
        try:
            os.remove(video.archivo.lstrip('/'))
        except Exception as e:
            print(f"Error eliminando archivo: {e}")
    
    # Eliminar de base de datos
    db.delete(video)
    db.commit()
    
    # Reorganizar ordenes
    videos_restantes = db.query(VideoPublicidad).filter(
        VideoPublicidad.orden > video.orden
    ).all()
    
    for v in videos_restantes:
        v.orden -= 1
    
    db.commit()
    
    return {"message": "Video eliminado correctamente"}

@router.put("/videos/reordenar")
async def reordenar_videos(
    orden_data: ActualizarOrdenVideo,
    db: Session = Depends(get_db)
):
    """Reordenar videos de publicidad"""
    
    for item in orden_data.videos_orden:
        video = db.query(VideoPublicidad).filter(
            VideoPublicidad.id == item["id"]
        ).first()
        if video:
            video.orden = item["orden"]
    
    db.commit()
    
    return {"message": "Orden actualizado correctamente"}

@router.put("/videos/{video_id}/toggle")
async def toggle_video_activo(video_id: int, db: Session = Depends(get_db)):
    """Activar/desactivar video"""
    video = db.query(VideoPublicidad).filter(VideoPublicidad.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video no encontrado")
    
    video.activo = not video.activo
    db.commit()
    
    return {
        "message": f"Video {'activado' if video.activo else 'desactivado'}",
        "activo": video.activo
    }

@router.get("/videos/random/activo")
async def obtener_video_aleatorio(db: Session = Depends(get_db)):
    """Obtener un video aleatorio para reproducir en cambio de cancha"""
    from sqlalchemy import func
    
    video = db.query(VideoPublicidad).filter(
        VideoPublicidad.activo == True
    ).order_by(func.random()).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="No hay videos activos disponibles")
    
    return {
        "id": video.id,
        "nombre": video.nombre,
        "archivo": video.archivo,
        "duracion": video.duracion
    }

@router.get("/videos/lista/activos")
async def obtener_lista_videos_activos(db: Session = Depends(get_db)):
    """Obtener lista de videos activos para las Raspberry Pi"""
    videos = db.query(VideoPublicidad).filter(
        VideoPublicidad.activo == True
    ).order_by(VideoPublicidad.orden).all()
    
    return [
        {
            "id": v.id,
            "nombre": v.nombre,
            "archivo": v.archivo,
            "duracion": v.duracion,
            "orden": v.orden
        }
        for v in videos
    ]