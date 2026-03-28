FROM python:3.11-slim

WORKDIR /app

# Зависимости отдельным слоем — кешируются если requirements.txt не менялся
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Исходники
COPY bot/ ./bot/
COPY main.py .

# Том для БД и логов — данные живут снаружи контейнера
VOLUME ["/app/data", "/app/logs"]

CMD ["python", "main.py"]
