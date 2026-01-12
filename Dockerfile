FROM python:3.12-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primeiro (cache)
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto do código
COPY . .

# Criar diretórios necessários
RUN mkdir -p uploads

# Copiar e dar permissão ao script de entrada
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Usar o script de entrada que trata PORT corretamente
ENTRYPOINT ["/app/entrypoint.sh"]
