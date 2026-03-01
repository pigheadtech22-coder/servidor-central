from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..mqtt_gateway import mqtt_bridge

router = APIRouter()


class CommandRequest(BaseModel):
    action: str
    payload: Dict[str, Any] = {}


@router.get("/estado")
async def estado_mqtt_bridge():
    return mqtt_bridge.snapshot()


@router.post("/canchas/{cancha_numero}/comando")
async def enviar_comando_cancha(cancha_numero: int, body: CommandRequest):
    if cancha_numero <= 0:
        raise HTTPException(status_code=400, detail="cancha_numero inválido")

    action = (body.action or "").strip()
    if not action:
        raise HTTPException(status_code=400, detail="action es requerido")

    try:
        topic = mqtt_bridge.publish_cancha_command(cancha_numero, action, body.payload)
        return {
            "ok": True,
            "topic": topic,
            "cancha_numero": cancha_numero,
            "action": action
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.post("/gateways/{gateway_id}/comando")
async def enviar_comando_gateway(gateway_id: str, body: CommandRequest):
    gateway_id = (gateway_id or "").strip()
    if not gateway_id:
        raise HTTPException(status_code=400, detail="gateway_id inválido")

    action = (body.action or "").strip()
    if not action:
        raise HTTPException(status_code=400, detail="action es requerido")

    try:
        topic = mqtt_bridge.publish_gateway_command(gateway_id, action, body.payload)
        return {
            "ok": True,
            "topic": topic,
            "gateway_id": gateway_id,
            "action": action
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
