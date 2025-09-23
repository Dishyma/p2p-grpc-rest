"""
Configuración de paths para imports
"""
import sys
from pathlib import Path

def setup_paths():
    """Configura los paths necesarios para imports de generated y src"""
    # Path al directorio src
    src_path = Path(__file__).parent.parent.parent
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    # Path al directorio generated para imports de gRPC
    gen_path = src_path / "generated"
    if str(gen_path) not in sys.path:
        sys.path.insert(0, str(gen_path))

# Ejecutar setup automáticamente al importar
setup_paths()
