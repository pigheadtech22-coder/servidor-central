# Servidor Central de Padel

Sistema de gestión centralizada para torneos de padel con múltiples canchas y dispositivos Raspberry Pi.

## 🏗️ Arquitectura

- **Servidor Central**: Python + FastAPI + SQLite (esta aplicación)
- **Raspberry Pi Marcador**: Cliente que se conecta al servidor central
- **Raspberry Pi Horarios**: Dashboard público con horarios y resultados

## 🚀 Instalación y Configuración

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Ejecutar el servidor
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Acceder al dashboard
- Dashboard principal: http://localhost:8000/dashboard
- Documentación API: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## 📡 API Endpoints

### Jugadores
- `GET /api/v1/jugadores` - Lista de jugadores
- `POST /api/v1/jugadores` - Crear jugador
- `POST /api/v1/jugadores/{id}/foto` - Subir foto

### Torneos
- `GET /api/v1/torneos` - Lista de torneos
- `POST /api/v1/torneos` - Crear torneo

### Partidos
- `GET /api/v1/partidos` - Lista de partidos
- `POST /api/v1/partidos` - Crear partido
- `PUT /api/v1/partidos/{id}/resultado` - Actualizar resultado

### Videos
- `GET /api/v1/videos` - Lista de videos
- `POST /api/v1/videos/upload` - Subir video
- `GET /api/v1/videos/random/activo` - Video aleatorio para cambio de cancha

### Estado de Canchas (para Raspberry Pi)
- `GET /api/cancha/{numero}/estado` - Estado actual de una cancha
- `POST /api/cancha/{numero}/resultado` - Recibir resultado del marcador

## 🎯 Configuración para Raspberry Pi

### Marcador (cliente del servidor central)
1. Modificar el marcador existente para obtener datos de: `GET /api/cancha/{numero}/estado`
2. Enviar resultados a: `POST /api/cancha/{numero}/resultado`
3. Obtener videos de: `GET /api/v1/videos/lista/activos`

### Dashboard de Horarios (pantalla pública)
- Acceder a: `http://servidor-central:8000/dashboard/horarios`
- Se actualiza automáticamente cada 30 segundos

## 📁 Estructura del Proyecto

```
servidor-central-padel/
├── app/
│   ├── main.py              # Servidor FastAPI principal
│   ├── database.py          # Configuración SQLite y modelos
│   ├── routers/             # Endpoints de la API
│   │   ├── jugadores.py
│   │   ├── torneos.py
│   │   ├── partidos.py
│   │   ├── videos.py
│   │   └── dashboard.py
│   └── static/              # Templates HTML del dashboard
├── database/                # Base de datos SQLite
├── uploads/                 # Archivos subidos (fotos, videos)
├── requirements.txt
└── README.md
```

## 🔧 Configuración de Red

Para que las Raspberry Pi se conecten al servidor central:

1. **Obtener IP del servidor**: `ipconfig` (Windows) o `ifconfig` (Linux/macOS)
2. **Configurar las Raspberry Pi** para apuntar a esta IP
3. **Abrir puerto 8000** en el firewall si es necesario

## 💾 Base de Datos

La base de datos SQLite se crea automáticamente en `database/padel_central.db` con las siguientes tablas:

- `jugadores` - Información de jugadores
- `torneos` - Datos de torneos
- `partidos` - Partidos programados y resultados
- `resultados_sets` - Detalles de cada set
- `videos_publicidad` - Videos para cambio de cancha
- `configuracion_sistema` - Configuraciones globales

## 🤝 Integración con Marcador Existente

Para conectar tu marcador actual al servidor central, modifica estas funciones:

```javascript
// Al iniciar el marcador
async function obtenerDatosPartido(canchaNumero) {
    const response = await fetch(`http://servidor-central:8000/api/cancha/${canchaNumero}/estado`);
    return await response.json();
}

// Al actualizar resultado
async function enviarResultado(canchaNumero, resultado) {
    await fetch(`http://servidor-central:8000/api/cancha/${canchaNumero}/resultado`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(resultado)
    });
}

// Para obtener videos de publicidad
async function obtenerVideos() {
    const response = await fetch(`http://servidor-central:8000/api/v1/videos/lista/activos`);
    return await response.json();
}
```

## 🔄 Estado del Sistema

El servidor mantiene el estado en tiempo real de:
- ✅ Partidos en progreso por cancha
- ✅ Horarios y próximos partidos
- ✅ Videos de publicidad centralizados
- ✅ Estadísticas de jugadores
- ✅ Estado de canchas (libre/ocupada)

## 📱 Dashboard Móvil

El dashboard web es responsive y funciona perfect en tablets y móviles para administrar el sistema desde cualquier dispositivo.

---

**¡Listo para revolucionar la gestión de torneos de padel! 🏓**