FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r backend/requirements.txt

# Ensure backend is a package
RUN touch backend/__init__.py

EXPOSE 10000

CMD ["gunicorn", "backend.app:app", "--bind", "0.0.0.0:10000"]