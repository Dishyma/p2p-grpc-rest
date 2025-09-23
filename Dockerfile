FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Copiar Pipfiles
COPY Pipfile Pipfile.lock ./

# Instalar pipenv y dependencias
RUN pip install --no-cache-dir pipenv && pipenv install --deploy --system && pip install --no-cache-dir click

# Copiar código
COPY src ./src

# Asegurar que Python encuentre los módulos en src
ENV PYTHONPATH=/app/src

# Generar código gRPC (idempotente)
RUN python -m src.proto.generate || true

CMD ["uvicorn", "src.directory_server.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
