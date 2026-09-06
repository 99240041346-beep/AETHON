FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY aethon ./aethon
EXPOSE 8000
CMD ["uvicorn", "aethon.main:app", "--host", "0.0.0.0", "--port", "8000"]
