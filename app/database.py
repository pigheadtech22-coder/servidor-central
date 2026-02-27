from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
import os

# Configuración de la base de datos
# Usa ruta local fuera de OneDrive para evitar problemas de file locking con SQLite
_local_db_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "padel_central")
os.makedirs(_local_db_dir, exist_ok=True)
DATABASE_URL = f"sqlite:///{os.path.join(_local_db_dir, 'padel_central.db')}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Modelos de la base de datos
class Jugador(Base):
    __tablename__ = "jugadores"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True)
    foto = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    email = Column(String, nullable=True)
    categoria = Column(String, default="6TA")  # 1RA, 2DA, 3RA, 4TA, 5TA, 6TA
    
    # Rankings diferenciados
    ranking_club = Column(Integer, default=0)
    ranking_torneo = Column(Integer, default=0)
    
    # Estadísticas
    partidos_jugados = Column(Integer, default=0)
    partidos_ganados = Column(Integer, default=0)
    
    fecha_creacion = Column(DateTime, default=func.now())
    activo = Column(Boolean, default=True)

class Torneo(Base):
    __tablename__ = "torneos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    fecha_inicio = Column(DateTime)
    fecha_fin = Column(DateTime, nullable=True)
    descripcion = Column(Text, nullable=True)
    num_canchas = Column(Integer, default=1)
    
    # Tipo: eliminacion, round_robin, grupos_eliminacion, liga, round_robin_liga
    tipo_torneo = Column(String, default="eliminacion") 
    
    # Configuración de reglas para el torneo
    num_sets = Column(Integer, default=3)
    puntos_set = Column(Integer, default=6)
    punto_oro = Column(Boolean, default=False)
    super_tiebreak_final = Column(Boolean, default=False)
    ventajas = Column(Boolean, default=True)
    
    reglas_especiales = Column(Text, nullable=True)
    activo = Column(Boolean, default=True)
    finalizado = Column(Boolean, default=False)
    
    # Relaciones
    categorias = relationship("Categoria", back_populates="torneo", cascade="all, delete-orphan")
    partidos = relationship("Partido", back_populates="torneo")

class Partido(Base):
    __tablename__ = "partidos"
    
    id = Column(Integer, primary_key=True, index=True)
    torneo_id = Column(Integer, ForeignKey("torneos.id"), nullable=True)
    categoria = Column(String, nullable=True)  # Referencia por nombre (compatibilidad)
    hora = Column(String, nullable=True)       # Ej: "19:00"
    turno = Column(Integer, nullable=True)     # Para cola de espera
    cancha_numero = Column(Integer, default=1)
    
    # Tipo: torneo, liga, club, libre
    tipo_partido = Column(String, default="club")
    
    # Jugadores
    jugador1_id = Column(Integer, ForeignKey("jugadores.id"))
    jugador2_id = Column(Integer, ForeignKey("jugadores.id"))
    jugador3_id = Column(Integer, ForeignKey("jugadores.id"))
    jugador4_id = Column(Integer, ForeignKey("jugadores.id"))
    
    # Estado del partido
    estado = Column(String, default="programado")  # programado, en_progreso, finalizado, cancelado
    fecha_programada = Column(DateTime)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)
    
    # Resultado
    sets_equipo1 = Column(Integer, default=0)
    sets_equipo2 = Column(Integer, default=0)
    ganador = Column(String, nullable=True)  # equipo1, equipo2
    
    # Reglas específicas para este partido (sobreescriben defaults)
    num_sets = Column(Integer, default=3)
    punto_oro = Column(Boolean, default=False)
    
    # Relaciones
    torneo = relationship("Torneo", back_populates="partidos")
    jugador1 = relationship("Jugador", foreign_keys=[jugador1_id])
    jugador2 = relationship("Jugador", foreign_keys=[jugador2_id])
    jugador3 = relationship("Jugador", foreign_keys=[jugador3_id])
    jugador4 = relationship("Jugador", foreign_keys=[jugador4_id])
    resultados = relationship("ResultadoSet", back_populates="partido", cascade="all, delete-orphan")

class Categoria(Base):
    __tablename__ = "categorias"
    id = Column(Integer, primary_key=True, index=True)
    torneo_id = Column(Integer, ForeignKey("torneos.id"))
    nombre = Column(String)  # Ej: "1ra Fuerza", "Femenino B"
    
    # Relaciones
    torneo = relationship("Torneo", back_populates="categorias")
    grupos = relationship("Grupo", back_populates="categoria", cascade="all, delete-orphan")

class Grupo(Base):
    __tablename__ = "grupos"
    id = Column(Integer, primary_key=True, index=True)
    categoria_id = Column(Integer, ForeignKey("categorias.id"))
    nombre = Column(String)  # Ej: "Grupo A", "Grupo 1"
    
    # Relaciones
    categoria = relationship("Categoria", back_populates="grupos")
    inscritos = relationship("Inscrito", back_populates="grupo", cascade="all, delete-orphan")

class Inscrito(Base):
    __tablename__ = "inscritos"
    id = Column(Integer, primary_key=True, index=True)
    grupo_id = Column(Integer, ForeignKey("grupos.id"))
    jugador1 = Column(String)
    jugador2 = Column(String, nullable=True)
    categoria = Column(String, nullable=True) # Cache de nombre de categoria
    
    # Relaciones
    grupo = relationship("Grupo", back_populates="inscritos")

class ResultadoSet(Base):
    __tablename__ = "resultados_sets"
    
    id = Column(Integer, primary_key=True, index=True)
    partido_id = Column(Integer, ForeignKey("partidos.id"))
    numero_set = Column(Integer)  # 1, 2, 3, 4, 5
    games_equipo1 = Column(Integer, default=0)
    games_equipo2 = Column(Integer, default=0)
    ganador_set = Column(String, nullable=True)  # equipo1, equipo2
    finalizado = Column(Boolean, default=False)
    
    # Relaciones
    partido = relationship("Partido", back_populates="resultados")

class VideoPublicidad(Base):
    __tablename__ = "videos_publicidad"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    archivo = Column(String)
    duracion = Column(Float, nullable=True)
    activo = Column(Boolean, default=True)
    orden = Column(Integer, default=0)
    fecha_subida = Column(DateTime, default=func.now())

class ConfiguracionSistema(Base):
    __tablename__ = "configuracion_sistema"
    
    id = Column(Integer, primary_key=True, index=True)
    clave = Column(String, unique=True, index=True)
    valor = Column(String)
    descripcion = Column(String, nullable=True)
    fecha_actualizacion = Column(DateTime, default=func.now())

class ConfiguracionSlide(Base):
    __tablename__ = "configuracion_slides"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)  # Resultados, Publicidad, Proximos Turnos, etc
    clave = Column(String, unique=True, index=True)  # resultados_recientes, publicidad, proximos_turnos
    activo = Column(Boolean, default=True)
    duracion = Column(Integer, default=15)  # Segundos
    orden = Column(Integer, default=0)
    parametros = Column(Text, nullable=True)  # JSON con configuraciones específicas
    fecha_actualizacion = Column(DateTime, default=func.now(), onupdate=func.now())

# Función para obtener sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Crear todas las tablas
def crear_tablas():
    Base.metadata.create_all(bind=engine)

# Función para inicializar configuraciones por defecto
def inicializar_configuraciones(db: Session):
    configuraciones_default = [
        {"clave": "puntos_set", "valor": "6", "descripcion": "Puntos necesarios para ganar un set"},
        {"clave": "ventaja", "valor": "true", "descripcion": "Usar ventaja en el marcador"},
        {"clave": "super_muerte_subita", "valor": "false", "descripcion": "Super muerte súbita en tercer set"},
        {"clave": "punto_oro", "valor": "false", "descripcion": "Punto de oro activo"},
        {"clave": "star_point", "valor": "false", "descripcion": "Star Point activo"},
        {"clave": "duracion_video_cambio", "valor": "30", "descripcion": "Duración en segundos del video en cambio de cancha"},
        {"clave": "modo_sistema", "valor": "club", "descripcion": "Modo actual del sistema: club o torneo"},
    ]
    
    for config in configuraciones_default:
        existing = db.query(ConfiguracionSistema).filter(
            ConfiguracionSistema.clave == config["clave"]
        ).first()
        if not existing:
            db_config = ConfiguracionSistema(**config)
            db.add(db_config)
    
    # Slides por defecto
    slides_default = [
        {"nombre": "Resultados Recientes", "clave": "resultados_recientes", "activo": True, "duracion": 15, "orden": 1},
        {"nombre": "Próximos Turnos", "clave": "proximos_turnos", "activo": True, "duracion": 15, "orden": 2},
        {"nombre": "Publicidad", "clave": "publicidad", "activo": True, "duracion": 30, "orden": 3},
        {"nombre": "Ranking Club", "clave": "ranking_club", "activo": False, "duracion": 15, "orden": 4},
        {"nombre": "Cuadro de Torneo", "clave": "cuadro_torneo", "activo": False, "duracion": 20, "orden": 5},
    ]
    
    for slide in slides_default:
        existing = db.query(ConfiguracionSlide).filter(
            ConfiguracionSlide.clave == slide["clave"]
        ).first()
        if not existing:
            db.add(ConfiguracionSlide(**slide))
    
    db.commit()
