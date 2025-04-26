FROM python:3.11-slim

# Arbeitsverzeichnis festlegen
WORKDIR /app

# Notwendige Pakete installieren
RUN apt-get update && apt-get install -y \
    ffmpeg \
    sqlite3 \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Python-Abhängigkeiten installieren
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendungscode kopieren
COPY app/ .

# Crontab einrichten für regelmäßige Ausführung
RUN echo "0 0 * * * python /app/scan_films.py > /proc/1/fd/1 2>/proc/1/fd/2" > /etc/cron.d/film-manager-cron \
    && chmod 0644 /etc/cron.d/film-manager-cron \
    && crontab /etc/cron.d/film-manager-cron

# Umgebungsvariablen
ENV FILM_DIR=/media/movies \
    DATABASE_PATH=/config/database.sqlite \
    CONFIG_PATH=/config/settings.json \
    SCAN_INTERVAL="0 0 * * *" \
    TZ=Europe/Berlin

# Volumes
VOLUME ["/media/movies", "/config", "/output"]

# Ports für die Weboberfläche
EXPOSE 8080

# Start-Skript ausführbar machen
RUN chmod +x /app/entrypoint.sh

# Startbefehl
CMD ["/app/entrypoint.sh"]