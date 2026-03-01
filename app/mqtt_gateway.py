import json
import os
import threading
from datetime import datetime
from typing import Any, Dict

try:
    import paho.mqtt.client as mqtt
except Exception:  # pragma: no cover
    mqtt = None


class MqttGatewayBridge:
    def __init__(self):
        self.host = os.getenv("CENTRAL_MQTT_HOST", "localhost")
        self.port = int(os.getenv("CENTRAL_MQTT_PORT", "1883"))
        self.username = os.getenv("CENTRAL_MQTT_USERNAME", "").strip()
        self.password = os.getenv("CENTRAL_MQTT_PASSWORD", "").strip()
        self.prefix = os.getenv("CENTRAL_MQTT_PREFIX", "central").strip() or "central"
        self.client_id = os.getenv("CENTRAL_MQTT_CLIENT_ID", "servidor-central-api").strip() or "servidor-central-api"

        self.client = None
        self.connected = False
        self.lock = threading.Lock()
        self.canchas_estado: Dict[int, Dict[str, Any]] = {}
        self.gateways_estado: Dict[str, Dict[str, Any]] = {}

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        self.connected = (rc == 0)
        if not self.connected:
            print(f"⚠️ MQTT central: conexión rechazada rc={rc}")
            return

        print(f"✅ MQTT central conectado a {self.host}:{self.port}")
        client.subscribe(f"{self.prefix}/canchas/+/estado", qos=1)
        client.subscribe(f"{self.prefix}/gateways/+/status", qos=1)
        client.subscribe(f"{self.prefix}/gateways/+/heartbeat", qos=0)

    def _on_disconnect(self, client, userdata, rc, properties=None):
        self.connected = False
        print(f"📴 MQTT central desconectado rc={rc}")

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        raw = msg.payload.decode("utf-8", errors="ignore")

        try:
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {"raw": raw}

        cancha_match = self._match_cancha_estado(topic)
        if cancha_match is not None:
            with self.lock:
                self.canchas_estado[cancha_match] = {
                    "topic": topic,
                    "payload": payload,
                    "updated_at": datetime.now().isoformat()
                }
            return

        gateway_match = self._match_gateway(topic)
        if gateway_match is not None:
            with self.lock:
                self.gateways_estado[gateway_match] = {
                    "topic": topic,
                    "payload": payload,
                    "updated_at": datetime.now().isoformat()
                }

    def _match_cancha_estado(self, topic: str):
        parts = topic.split("/")
        if len(parts) == 4 and parts[0] == self.prefix and parts[1] == "canchas" and parts[3] == "estado":
            try:
                return int(parts[2])
            except Exception:
                return None
        return None

    def _match_gateway(self, topic: str):
        parts = topic.split("/")
        if len(parts) == 4 and parts[0] == self.prefix and parts[1] == "gateways" and parts[3] in ("status", "heartbeat"):
            return parts[2]
        return None

    def start(self):
        if mqtt is None:
            print("⚠️ paho-mqtt no disponible, puente MQTT central deshabilitado")
            return False

        if self.client is not None:
            return True

        self.client = mqtt.Client(client_id=self.client_id, clean_session=True)
        if self.username:
            self.client.username_pw_set(self.username, self.password or None)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.reconnect_delay_set(min_delay=1, max_delay=15)

        try:
            self.client.connect(self.host, self.port, keepalive=20)
            self.client.loop_start()
            return True
        except Exception as error:
            self.client = None
            print(f"❌ No se pudo iniciar MQTT central: {error}")
            return False

    def stop(self):
        if self.client is None:
            return

        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass
        finally:
            self.client = None
            self.connected = False

    def publish_cancha_command(self, cancha_numero: int, action: str, payload: Dict[str, Any]):
        if self.client is None:
            raise RuntimeError("Cliente MQTT central no inicializado")

        topic = f"{self.prefix}/canchas/{cancha_numero}/cmd/{action}"
        message = json.dumps(payload or {})
        info = self.client.publish(topic, message, qos=1, retain=False)

        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"Error publicando comando MQTT rc={info.rc}")

        return topic

    def publish_gateway_command(self, gateway_id: str, action: str, payload: Dict[str, Any]):
        if self.client is None:
            raise RuntimeError("Cliente MQTT central no inicializado")

        topic = f"{self.prefix}/gateways/{gateway_id}/cmd/{action}"
        message = json.dumps(payload or {})
        info = self.client.publish(topic, message, qos=1, retain=False)

        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"Error publicando comando MQTT rc={info.rc}")

        return topic

    def snapshot(self):
        with self.lock:
            return {
                "connected": self.connected,
                "broker": {
                    "host": self.host,
                    "port": self.port,
                    "prefix": self.prefix,
                    "client_id": self.client_id
                },
                "canchas_estado": self.canchas_estado.copy(),
                "gateways_estado": self.gateways_estado.copy()
            }


mqtt_bridge = MqttGatewayBridge()
