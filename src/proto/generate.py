#!/usr/bin/env python3
"""
Script para generar código gRPC desde archivos .proto
"""
import subprocess
import sys
import os
from pathlib import Path

def generate_grpc_code():
    """Genera código Python desde archivos .proto"""

    # Rutas
    proto_dir = Path(__file__).parent
    src_dir = proto_dir.parent
    proto_file = proto_dir / "file_service.proto"

    # Crear directorio para código generado si no existe
    generated_dir = src_dir / "generated"
    generated_dir.mkdir(exist_ok=True)

    # Comando para generar código gRPC
    command = [
        sys.executable, "-m", "grpc_tools.protoc",
        f"--proto_path={proto_dir}",
        f"--python_out={generated_dir}",
        f"--grpc_python_out={generated_dir}",
        str(proto_file)
    ]

    print(f"Generando código gRPC desde {proto_file}")
    print(f"Comando: {' '.join(command)}")

    try:
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Código gRPC generado exitosamente")

            # Crear archivo __init__.py si no existe
            init_file = generated_dir / "__init__.py"
            if not init_file.exists():
                init_file.touch()

            print(f"📁 Archivos generados en: {generated_dir}")
            for file in generated_dir.glob("*.py"):
                print(f"   - {file.name}")

        else:
            print("❌ Error generando código gRPC:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False

    except FileNotFoundError:
        print("❌ Error: grpc_tools.protoc no está instalado")
        print("Instala con: pip install grpcio-tools")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

    return True

if __name__ == "__main__":
    success = generate_grpc_code()
    sys.exit(0 if success else 1)
