FROM python:3.14-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-bebas-neue fonts-montserrat tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

RUN useradd -r app
USER app

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8080/health')"

CMD ["python", "-u", "app.py"]
