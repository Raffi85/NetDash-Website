FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r backend/requirements.txt

RUN touch backend/__init__.py

EXPOSE 10000

CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:10000", "app:app"]

