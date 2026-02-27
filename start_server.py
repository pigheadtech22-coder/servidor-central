#!/usr/bin/env python
"""
Script para iniciar el servidor central FastAPI
"""
import os
import sys
import subprocess

# Asegurar que estamos en el directorio correcto
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

print(f"Iniciando servidor desde: {os.getcwd()}")
print("=" * 50)

try:
    # Verificar que podemos importar la aplicación
    from app.main import app
    print("✅ Aplicación importada correctamente")
    
    # Iniciar uvicorn
    import uvicorn
    print("🚀 Iniciando servidor FastAPI...")
    print("📍 URL: http://localhost:8000")
    print("📊 Dashboard: http://localhost:8000/dashboard")
    print("⚙️ Docs: http://localhost:8000/docs")
    print("=" * 50)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
    
except ImportError as e:
    print(f"❌ Error importando aplicación: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error iniciando servidor: {e}")
    sys.exit(1)