FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# ساخت دیتابیس هنگام build (اگر نبود، در استارت هم ساخته می‌شود)
RUN python seed.py 50000
ENV PORT=8000
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
