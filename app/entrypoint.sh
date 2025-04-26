#!/bin/bash
set -e

# Konfigurationsverzeichnis erstellen, falls nicht vorhanden
mkdir -p /config

# Datenbank initialisieren, falls nicht vorhanden
if [ ! -f "$DATABASE_PATH" ]; then
    echo "Initialisiere Datenbank..."
    python /app/init_db.py
fi

# Standardkonfiguration erstellen, falls nicht vorhanden
if [ ! -f "$CONFIG_PATH" ]; then
    echo "Erstelle Standardkonfiguration..."
    cat > "$CONFIG_PATH" << EOF
{
    "film_alter_tage": 365,
    "nicht_abgespielt_tage": 180,
    "aktion": "bericht",
    "jellyfin_url": "http://jellyfin:8096",
    "jellyfin_api_key": "",
    "film_ordner": "/media/movies",
    "ausgabe_ordner": "/output",
    "log_level": "INFO",
    "ausnahmen": []
}
EOF
fi

# Cron Service starten
service cron start

# Flask-Anwendung im Hintergrund starten
python /app/app.py &

# Auf Nutzerinteraktion warten und den Status ausgeben
echo "Film-Manager gestartet. Weboberfläche verfügbar unter http://[IP]:8080"
echo "Konfiguration in $CONFIG_PATH"

# Container am Laufen halten
tail -f /dev/null