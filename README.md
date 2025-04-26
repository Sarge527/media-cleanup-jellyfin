# media cleanup jellyfin
 removes all old media files form your server, which are unwatched or never watched

# Media Cleanup für Jellyfin

Ein Docker-Container für Unraid, der ältere und nicht mehr angesehene Filme automatisch identifiziert, damit du deinen Speicherplatz optimieren kannst.

## Funktionen

- Identifiziert Filme, die älter als ein bestimmter Zeitraum sind
- Erkennt Filme, die seit einem definierbaren Zeitraum nicht mehr abgespielt wurden
- Generiert detaillierte Berichte über diese Filme
- Optional: Verschieben oder Löschen der identifizierten Filme
- Weboberfläche zur einfachen Konfiguration und Überwachung
- Integration mit Jellyfin zur Ermittlung der letzten Wiedergabedaten

## Installation

### Installation mit Docker Compose

1. Klone dieses Repository:
   ```bash
   git clone https://github.com/dein-username/media-cleanup-jellyfin.git
   cd media-cleanup-jellyfin
   ```

2. Passe die `docker-compose.yml` an deine Bedürfnisse an:
   ```yaml
   version: '3'
   services:
     media-cleanup:
       build: .
       container_name: media-cleanup-jellyfin
       environment:
         - TZ=Europe/Berlin
         - PUID=1000
         - PGID=1000
       volumes:
         - ./config:/config
         - /pfad/zu/movies:/media/movies
         - ./output:/output
       ports:
         - 8080:8080
       restart: unless-stopped
   ```

3. Starte den Container:
   ```bash
   docker-compose up -d
   ```

### Installation in Unraid

1. Gehe in Unraid zu "Docker" Tab
2. Klicke auf "Add Container"
3. Repository: `dein-username/media-cleanup-jellyfin`
4. Setze die folgenden Einstellungen:
   - Name: media-cleanup-jellyfin
   - Netzwerktyp: Bridge
   - Port: 8080:8080
   - Volumen 1: `/mnt/user/appdata/media-cleanup:/config`
   - Volumen 2: `/mnt/user/movies:/media/movies`
   - Volumen 3: `/mnt/user/appdata/media-cleanup/output:/output`
   - Umgebungsvariable: `TZ=Europe/Berlin`

5. Klicke auf "Apply"

## Konfiguration

Nach dem Start des Containers ist die Weboberfläche unter `http://deine-ip:8080` erreichbar. Hier kannst du folgende Einstellungen vornehmen:

- **Film-Alter (Tage)**: Filme älter als dieser Wert werden berücksichtigt
- **Nicht abgespielt (Tage)**: Filme, die länger als dieser Zeitraum nicht abgespielt wurden
- **Aktion**: Was mit den identifizierten Filmen geschehen soll
  - Nur Bericht erstellen
  - In Archiv verschieben
  - Löschen (Vorsicht!)
- **Jellyfin URL**: Die URL deines Jellyfin-Servers
- **Jellyfin API-Key**: API-Schlüssel für den Zugriff auf Jellyfin
- **Film-Ordner**: Der Pfad zu deinen Filmen im Container
- **Ausgabe-Ordner**: Wo die Berichte gespeichert werden sollen
- **Ausnahmen**: Filme, die bestimmte Zeichenketten im Pfad enthalten, werden ignoriert

## Jellyfin-Integration einrichten

1. Öffne deine Jellyfin-Instanz
2. Gehe zu Dashboard → Erweitert → API-Schlüssel
3. Erstelle einen neuen API-Schlüssel
4. Kopiere diesen Schlüssel in die Konfiguration des Media Cleanup Containers

## Manuellen Scan starten

Auf der Hauptseite der Weboberfläche kannst du jederzeit einen manuellen Scan starten, indem du auf "Scan jetzt starten" klickst.

## Automatischer Scan

Standardmäßig wird täglich um Mitternacht ein automatischer Scan durchgeführt. Die Ergebnisse werden in der Weboberfläche unter "Berichte" angezeigt.

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert.