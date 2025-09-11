FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Copiar Pipfiles
COPY Pipfile Pipfile.lock ./

# Instalar pipenv y dependencias
RUN pip install pipenv && pipenv install --deploy --system

# Copiar código
COPY src ./src

CMD ["uvicorn", "src.directory_server.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
