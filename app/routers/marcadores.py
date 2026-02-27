from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from typing import List, Optional
import ipaddress

from ..database import get_db, Base

router = APIRouter()

# Modelo para marcadores registrados
class MarcadorRegistrado(Base):
    __tablename__ = "marcadores_registrados"
    
    id = Column(Integer, primary_key=True, index=True)
    cancha_numero = Column(Integer, nullable=False, index=True)
    nombre = Column(String, nullable=False)
    ubicacion = Column(String, nullable=True)
    ip_address = Column(String, nullable=False)
    puerto = Column(Integer, default=5173)
    version = Column(String, nullable=True)
    ultima_conexion = Column(DateTime, default=func.now())
    activo = Column(Boolean, default=True)
    configuracion = Column(Text, nullable=True)  # JSON string con config adicional
    fecha_registro = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<Marcador(cancha={self.cancha_numero}, ip={self.ip_address})>"

# Asegurar que la tabla existe
from ..database import SessionLocal, engine
Base.metadata.create_all(bind=engine, tables=[MarcadorRegistrado.__table__])

@router.post("/registrar")
async def registrar_marcador(
    marcador_data: dict,
    request: Request,
    db: Session = Depends(get_db)
):
    """Registrar un nuevo marcador o actualizar uno existente"""
    try:
        # Obtener IP real del cliente
        client_ip = request.client.host
        if marcador_data.get('ip_address'):
            # Usar la IP proporcionada si es válida
            try:
                ipaddress.ip_address(marcador_data['ip_address'])
                client_ip = marcador_data['ip_address']
            except ValueError:
                pass  # Usar la IP detectada
        
        cancha_numero = marcador_data.get('cancha_numero')
        if not cancha_numero:
            raise HTTPException(status_code=400, detail="cancha_numero es requerido")
        
        # Buscar marcador existente por cancha
        marcador_existente = db.query(MarcadorRegistrado).filter(
            MarcadorRegistrado.cancha_numero == cancha_numero
        ).first()
        
        if marcador_existente:
            # Si fue desconectado forzosamente por el admin, no permitir re-registro
            if not marcador_existente.activo:
                return {
                    "status": "desconectado",
                    "activo": False,
                    "cancha_numero": cancha_numero,
                    "message": "Este marcador fue desconectado por el administrador. Contacta al admin para reconectarlo."
                }

            # Actualizar marcador existente
            marcador_existente.nombre = marcador_data.get('nombre', marcador_existente.nombre)
            marcador_existente.ubicacion = marcador_data.get('ubicacion', marcador_existente.ubicacion)
            marcador_existente.ip_address = client_ip
            marcador_existente.puerto = marcador_data.get('puerto', marcador_existente.puerto)
            marcador_existente.version = marcador_data.get('version', marcador_existente.version)
            marcador_existente.ultima_conexion = datetime.now()
            marcador_existente.activo = True
            
            db.commit()
            db.refresh(marcador_existente)
            
            return {
                "message": "Marcador actualizado",
                "marcador_id": marcador_existente.id,
                "cancha_numero": cancha_numero,
                "ip_detectada": client_ip,
                "activo": True,
                "status": "updated"
            }
        else:
            # Crear nuevo marcador
            nuevo_marcador = MarcadorRegistrado(
                cancha_numero=cancha_numero,
                nombre=marcador_data.get('nombre', f"Marcador Cancha {cancha_numero}"),
                ubicacion=marcador_data.get('ubicacion', 'Sin especificar'),
                ip_address=client_ip,
                puerto=marcador_data.get('puerto', 5173),
                version=marcador_data.get('version'),
                ultima_conexion=datetime.now()
            )
            
            db.add(nuevo_marcador)
            db.commit()
            db.refresh(nuevo_marcador)
            
            return {
                "message": "Marcador registrado",
                "marcador_id": nuevo_marcador.id,
                "cancha_numero": cancha_numero,
                "ip_detectada": client_ip,
                "activo": True,
                "status": "created"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error registrando marcador: {str(e)}")


@router.post("/heartbeat")
async def heartbeat_marcador(
    marcador_data: dict,
    request: Request,
    db: Session = Depends(get_db)
):
    """Heartbeat ligero para auto-vinculación de marcador por IP desde TV sin teclado/mouse."""
    try:
      client_ip = request.client.host
      provided_ip = (marcador_data.get('ip_address') or '').strip()
      if provided_ip:
          try:
              ipaddress.ip_address(provided_ip)
              client_ip = provided_ip
          except ValueError:
              pass

      marcador = db.query(MarcadorRegistrado).filter(
          MarcadorRegistrado.ip_address == client_ip
      ).first()

      if not marcador:
          return {
              "status": "unassigned",
              "message": "Marcador no asignado en servidor central",
              "ip_detectada": client_ip,
              "assigned": False
          }

      marcador.ultima_conexion = datetime.now()
      if marcador_data.get('version'):
          marcador.version = marcador_data.get('version')
      if marcador_data.get('nombre'):
          marcador.nombre = marcador_data.get('nombre')
      if marcador_data.get('puerto'):
          marcador.puerto = marcador_data.get('puerto')

      db.commit()
      db.refresh(marcador)

      if not marcador.activo:
          return {
              "status": "desconectado",
              "message": "Marcador desautorizado por administrador",
              "ip_detectada": client_ip,
              "assigned": False,
              "activo": False
          }

      return {
          "status": "assigned",
          "message": "Marcador asignado por servidor central",
          "assigned": True,
          "activo": True,
          "ip_detectada": client_ip,
          "marcador_id": marcador.id,
          "cancha_numero": marcador.cancha_numero,
          "nombre": marcador.nombre,
          "puerto": marcador.puerto
      }
    except Exception as e:
      raise HTTPException(status_code=500, detail=f"Error en heartbeat de marcador: {str(e)}")

@router.get("/lista")
async def listar_marcadores(
    activos_solo: bool = True,
    db: Session = Depends(get_db)
):
    """Obtener lista de marcadores registrados"""
    query = db.query(MarcadorRegistrado)
    
    if activos_solo:
        # Considerar activos aquellos que se conectaron en las últimas 2 horas
        limite_tiempo = datetime.now() - timedelta(hours=2)
        query = query.filter(
            MarcadorRegistrado.activo == True,
            MarcadorRegistrado.ultima_conexion >= limite_tiempo
        )
    
    marcadores = query.order_by(MarcadorRegistrado.cancha_numero).all()
    
    resultado = []
    for marcador in marcadores:
        # Calcular tiempo desde última conexión
        tiempo_desconectado = datetime.now() - marcador.ultima_conexion
        estado_conexion = "online" if tiempo_desconectado < timedelta(minutes=10) else "offline"
        
        resultado.append({
            "id": marcador.id,
            "cancha_numero": marcador.cancha_numero,
            "nombre": marcador.nombre,
            "ubicacion": marcador.ubicacion,
            "ip_address": marcador.ip_address,
            "puerto": marcador.puerto,
            "version": marcador.version,
            "ultima_conexion": marcador.ultima_conexion.isoformat(),
            "estado_conexion": estado_conexion,
            "tiempo_desconectado_minutos": int(tiempo_desconectado.total_seconds() / 60),
            "url_acceso": f"http://{marcador.ip_address}:{marcador.puerto}",
            "fecha_registro": marcador.fecha_registro.isoformat()
        })
    
    return {
        "marcadores": resultado,
        "total": len(resultado),
        "timestamp": datetime.now().isoformat()
    }

@router.post("/ping/{cancha_numero}")
async def ping_marcador(
    cancha_numero: int,
    db: Session = Depends(get_db)
):
    """Probar conexión con un marcador específico"""
    marcador = db.query(MarcadorRegistrado).filter(
        MarcadorRegistrado.cancha_numero == cancha_numero
    ).first()
    
    if not marcador:
        raise HTTPException(status_code=404, detail="Marcador no encontrado")
    
    try:
        import requests
        url = f"http://{marcador.ip_address}:{marcador.puerto}/"
        
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            # Actualizar última conexión
            marcador.ultima_conexion = datetime.now()
            db.commit()
            
            return {
                "cancha_numero": cancha_numero,
                "status": "online",
                "response_time_ms": int(response.elapsed.total_seconds() * 1000),
                "url": url
            }
        else:
            return {
                "cancha_numero": cancha_numero,
                "status": "error",
                "error": f"HTTP {response.status_code}"
            }
            
    except requests.exceptions.Timeout:
        return {
            "cancha_numero": cancha_numero,
            "status": "timeout",
            "error": "Timeout - marcador no responde"
        }
    except Exception as e:
        return {
            "cancha_numero": cancha_numero,
            "status": "error",
            "error": str(e)
        }

@router.delete("/{marcador_id}")
async def eliminar_marcador(
    marcador_id: int,
    db: Session = Depends(get_db)
):
    """Desconectar un marcador (soft-delete: lo marca como inactivo).
    El marcador seguirá recibiendo un estado 'desconectado' en su próximo heartbeat.
    Para volver a conectarlo usa POST /reconectar/{cancha_numero}.
    """
    marcador = db.query(MarcadorRegistrado).filter(MarcadorRegistrado.id == marcador_id).first()

    if not marcador:
        raise HTTPException(status_code=404, detail="Marcador no encontrado")

    # Soft-delete: marcar como inactivo en lugar de borrar el registro
    marcador.activo = False
    marcador.ultima_conexion = datetime.now()
    db.commit()

    return {"message": "Marcador desconectado", "marcador_id": marcador_id, "activo": False}


@router.post("/reconectar/{cancha_numero}")
async def reconectar_marcador(
    cancha_numero: int,
    db: Session = Depends(get_db)
):
    """Re-autorizar el marcador de una cancha que fue desconectado previamente."""
    marcador = db.query(MarcadorRegistrado).filter(
        MarcadorRegistrado.cancha_numero == cancha_numero
    ).first()

    if not marcador:
        raise HTTPException(status_code=404, detail=f"No hay registro de marcador para cancha {cancha_numero}")

    marcador.activo = True
    marcador.ultima_conexion = datetime.now()
    db.commit()

    return {"message": f"Marcador cancha {cancha_numero} re-autorizado", "activo": True}

@router.put("/{marcador_id}")
async def actualizar_marcador(
    marcador_id: int,
    marcador_data: dict,
    db: Session = Depends(get_db)
):
    """Actualizar información de un marcador"""
    marcador = db.query(MarcadorRegistrado).filter(MarcadorRegistrado.id == marcador_id).first()
    
    if not marcador:
        raise HTTPException(status_code=404, detail="Marcador no encontrado")
    
    # Actualizar campos permitidos
    if 'nombre' in marcador_data:
        marcador.nombre = marcador_data['nombre']
    if 'ubicacion' in marcador_data:
        marcador.ubicacion = marcador_data['ubicacion']
    if 'activo' in marcador_data:
        marcador.activo = marcador_data['activo']
    
    db.commit()
    db.refresh(marcador)
    
    return {"message": "Marcador actualizado", "marcador_id": marcador_id}

@router.get("/estadisticas")
async def obtener_estadisticas_marcadores(db: Session = Depends(get_db)):
    """Obtener estadísticas de marcadores conectados"""
    total_marcadores = db.query(MarcadorRegistrado).count()
    marcadores_activos = db.query(MarcadorRegistrado).filter(
        MarcadorRegistrado.activo == True
    ).count()
    
    # Marcadores online (conectados en últimos 10 minutos)
    limite_online = datetime.now() - timedelta(minutes=10)
    marcadores_online = db.query(MarcadorRegistrado).filter(
        MarcadorRegistrado.ultima_conexion >= limite_online
    ).count()
    
    # Canchas con marcadores asignados
    canchas_con_marcador = db.query(MarcadorRegistrado.cancha_numero).distinct().count()
    
    return {
        "total_marcadores": total_marcadores,
        "marcadores_activos": marcadores_activos,
        "marcadores_online": marcadores_online,
        "canchas_con_marcador": canchas_con_marcador,
        "timestamp": datetime.now().isoformat()
    }