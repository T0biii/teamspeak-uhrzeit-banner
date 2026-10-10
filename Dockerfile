FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-bebas-neue fonts-montserrat tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir pillow

WORKDIR /app
COPY app.py .

RUN useradd -r app
USER app

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8080/health')"

CMD ["python", "-u", "app.py"]
