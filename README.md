# Sistema P2P de Compartición de Archivos

![Python](https://img.shields.io/badge/python-v3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-green.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)
![Docker](https://img.shields.io/badge/docker-latest-blue.svg)
![gRPC](https://img.shields.io/badge/gRPC-latest-orange.svg)

Sistema peer-to-peer descentralizado para compartición de archivos con servidor de directorio centralizado y transferencia directa entre peers mediante gRPC.

## 🎯 Características Principales

- **Arquitectura Híbrida**: Directorio centralizado con transferencia P2P directa
- **Transferencia Eficiente**: Streaming de archivos grandes mediante gRPC con chunking
- **Auto-descubrimiento**: Registro automático de peers y anuncio de archivos
- **CLI Intuitivo**: Interface de línea de comandos fácil de usar
- **Observabilidad**: Logs estructurados y métricas de performance
- **Calidad**: Tests automatizados y pre-commit hooks

## 🏗️ Arquitectura

```
┌─────────────────┐    REST API    ┌─────────────────┐
│   Directory     │◄──────────────►│     Peer 1      │
│    Server       │                │  (gRPC Server)  │
│  (PostgreSQL)   │                └─────────────────┘
└─────────────────┘                          │
         ▲                                   │ gRPC
         │ REST API                          │ File Transfer
         │                                   ▼
┌─────────────────┐                ┌─────────────────┐
│     Peer 2      │◄──────────────►│     Peer 3      │
│  (gRPC Server)  │   gRPC File    │  (gRPC Server)  │
└─────────────────┘    Transfer    └─────────────────┘
```

## 🛠️ Stack Tecnológico

- **Backend**: Python 3.9+ con FastAPI
- **Base de Datos**: PostgreSQL 14+
- **Comunicación**: gRPC para transferencia P2P, REST para directorio
- **Containerización**: Docker + Docker Compose
- **Calidad**: pytest, black, flake8, pre-commit hooks
- **Observabilidad**: structlog para logging estructurado

## 📁 Estructura del Proyecto

```
p2p-system/
├── .github/workflows/ci.yml       # CI/CD pipeline
├── .pre-commit-config.yaml        # Pre-commit hooks
├── Makefile                       # Comandos de desarrollo
├── docker-compose.yml             # Orquestación de servicios
├── requirements/                  # Dependencias
│   ├── base.txt
│   ├── dev.txt
│   └── test.txt
├── src/
│   ├── directory_server/          # Servidor de directorio (FastAPI)
│   │   ├── main.py
│   │   ├── api/                   # Endpoints REST
│   │   ├── models/                # Modelos SQLAlchemy
│   │   ├── services/              # Lógica de negocio
│   │   └── config.py
│   ├── peer/                      # Aplicación peer
│   │   ├── main.py
│   │   ├── grpc_services/         # Servicios gRPC
│   │   ├── rest_client/           # Cliente REST
│   │   └── config.py
│   ├── proto/                     # Definiciones Protocol Buffers
│   │   ├── file_service.proto
│   │   └── generate.py
│   └── shared/                    # Código compartido
│       ├── database.py
│       ├── logging_config.py
│       └── models.py
├── tests/                         # Suite de pruebas
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── configs/                       # Configuraciones de peers
│   ├── directory_server.env
│   ├── peer1.env
│   ├── peer2.env
│   └── peer3.env
└── docs/                          # Documentación
    └── api/
```

## 🚀 Inicio Rápido

### Prerrequisitos

- Docker y Docker Compose
- Python 3.9+
- Make (opcional, para comandos simplificados)

### Instalación y Ejecución

1. **Clonar el repositorio**
   ```bash
   git clone <repository-url>
   cd p2p-system
   ```

2. **Configurar el entorno**
   ```bash
   make setup
   ```

3. **Levantar el sistema completo**
   ```bash
   make dev-up
   ```
   Esto iniciará:
   - Directory Server (puerto 8080)
   - PostgreSQL (puerto 5432)
   - 3 peers de ejemplo (puertos gRPC: 50051, 50052, 50053)

4. **Verificar que funciona**
   ```bash
   # Health check del directory server
   curl http://localhost:8080/api/v1/health
   
   # Ver documentación interactiva
   open http://localhost:8080/docs
   ```

## 💻 Uso del Sistema

### Interface CLI

Accede a la CLI de cualquier peer:

```bash
# Entrar al container del peer1
make peer-shell PEER=peer1

# Una vez dentro, iniciar la CLI
python -m peer.cli
```

### Comandos Disponibles

```
p2p> list                    # Ver archivos locales
p2p> search video.mp4        # Buscar archivo en la red
p2p> download video.mp4      # Descargar archivo
p2p> peers                   # Ver peers activos
p2p> status                  # Estado del peer actual
p2p> quit                    # Salir
```

### Ejemplo de Flujo Completo

```bash
# Terminal 1: Peer1 (tiene video.mp4)
p2p> list
Local files:
- video.mp4 (1.2GB)

# Terminal 2: Peer2 (quiere descargar)
p2p> search video.mp4
Found 1 peer(s) with 'video.mp4':
- peer-001 (127.0.0.1:50051)

p2p> download video.mp4
Downloading from peer-001...
Progress: ████████████████████ 100% (1.2GB/1.2GB)
✓ Download completed successfully
✓ File announced to network

# Ahora peer2 también puede servir el archivo
```

## 🧪 Testing

### Ejecutar Tests

```bash
# Todos los tests
make test

# Solo tests unitarios
pytest tests/unit/

# Tests de integración
pytest tests/integration/

# Tests de carga
make load-test
```

### Coverage

```bash
# Ver coverage
make test-coverage
```

## 📊 API Reference

### Directory Server (REST API)

Base URL: `http://localhost:8080/api/v1`

#### Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/peers/register` | Registrar nuevo peer |
| DELETE | `/peers/{peer_id}` | Desregistrar peer |
| GET | `/files/search?filename=<name>` | Buscar archivo |
| POST | `/files/announce` | Anunciar archivos |
| POST | `/peers/heartbeat` | Mantener peer activo |
| GET | `/health` | Health check |
| GET | `/docs` | Documentación Swagger |

#### Ejemplo de Registro de Peer

```bash
curl -X POST http://localhost:8080/api/v1/peers/register \
  -H "Content-Type: application/json" \
  -d '{
    "peer_id": "peer-1",
    "ip": "127.0.0.1",
    "grpc_port": 50051,
    "files": ["video.mp4", "document.pdf"]
  }'
```

### Peer gRPC Service

Servicios disponibles:
- `ListFiles`: Listar archivos del peer
- `DownloadFile`: Descargar archivo (streaming)
- `GetFileInfo`: Obtener información del archivo

## 🛠️ Comandos de Desarrollo

```bash
# Setup inicial
make setup              # Instalar dependencias + pre-commit hooks

# Desarrollo
make dev-up             # Levantar todos los servicios
make dev-down           # Bajar servicios y limpiar volúmenes
make logs               # Ver logs en tiempo real

# Calidad de código
make lint               # black + flake8 + isort
make test               # Ejecutar tests con coverage
make proto              # Generar archivos de Protocol Buffers

# Limpieza
make clean              # Limpiar containers y volúmenes
```

## 📈 Performance y Observabilidad

### Logs Estructurados

Todos los servicios usan `structlog` para logging estructurado:

```python
logger.info(
    "File download started",
    peer_id=self.peer_id,
    filename=filename,
    source_peer=source_peer,
    file_size=file_size,
    trace_id=trace_id
)
```

### Métricas

- Duración de descargas
- Número de descargas activas
- Bytes transferidos
- Latencia de requests

## 🔧 Configuración

### Variables de Entorno por Peer

```env
# configs/peer1.env
PEER_ID=peer-001
PEER_IP=0.0.0.0
GRPC_PORT=50051
FILES_DIRECTORY=./data/peer1_files
DIRECTORY_SERVER_URL=http://directory-server:8080/api/v1
HEARTBEAT_INTERVAL=30
LOG_LEVEL=INFO
```

## 🚢 Deployment

### Desarrollo Local
```bash
make dev-up
```

### Futuro: Producción (AWS/Kubernetes)
- EKS para orquestación
- RDS PostgreSQL
- Application Load Balancer
- CloudWatch para observabilidad

## 🤝 Contribución

1. Crear feature branch
2. Hacer cambios
3. Ejecutar `make lint` y `make test`
4. Pre-commit hooks se ejecutan automáticamente
5. Crear Pull Request

### Pre-commit Hooks Configurados
- black (formatting)
- flake8 (linting)
- isort (import sorting)

## 🐛 Troubleshooting

### Problemas Comunes

**Peer no se registra:**
- Verificar que directory server esté ejecutándose
- Revisar configuración de red en docker-compose.yml

**Descarga falla:**
- Verificar que el peer origen esté activo
- Revisar logs del peer: `docker-compose logs peer1`

**Tests fallan:**
- Asegurar que todos los servicios estén down: `make dev-down`
- Limpiar containers: `make clean`

### Ver Logs
```bash
# Todos los servicios
make logs

# Servicio específico
docker-compose logs -f directory-server
docker-compose logs -f peer1
```

## 📋 Roadmap

- [x] **Sprint 1**: Setup + Directory Server básico
- [x] **Sprint 2**: Peer básico + gRPC transferencia
- [x] **Sprint 3**: Integración completa + tests
- [x] **Sprint 4**: Documentación + demo
- [ ] **Futuro**: Deployment AWS/Kubernetes
- [ ] **Futuro**: Replicación de archivos
- [ ] **Futuro**: Cifrado end-to-end

## 📄 Licencia

[Especificar licencia]

## 👥 Equipo

- **Desarrollador 1**: Backend + Integración
- **Desarrollador 2**: APIs + Testing

## 📞 Soporte

Para problemas o preguntas:
- Abrir issue en GitHub
- Revisar documentación en `/docs`
- Consultar logs para debugging