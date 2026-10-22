FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd -r -u 10001 appuser
COPY app.py .
USER appuser
EXPOSE 5002
CMD ["gunicorn", "--bind", "0.0.0.0:5002", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
