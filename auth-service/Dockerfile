FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY auth-service/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY shared ./shared

COPY auth-service/app ./app

EXPOSE 7000

CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","7000"]