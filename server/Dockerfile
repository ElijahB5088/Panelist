FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY migrations ./migrations
RUN useradd --create-home --uid 10001 panelist \
	&& mkdir -p /app/data \
	&& chown -R panelist:panelist /app

ENV PYTHONPATH=/app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
	CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/ready', timeout=3)"
USER panelist
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
