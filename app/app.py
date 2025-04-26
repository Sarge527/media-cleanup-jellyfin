#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import sqlite3
import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Konfiguration
CONFIG_PATH = os.environ.get('CONFIG_PATH', '/config/settings.json')
DATABASE_PATH = os.environ.get('DATABASE_PATH', '/config/database.sqlite')

# HTML-Templates als Strings definieren (da wir keine separate templates-Ordner haben)
# In einer komplexeren Anwendung würde man diese in separate Dateien auslagern
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Media Cleanup für Jellyfin</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }
        h1, h2, h3 {
            color: #333;
        }
        .card {
            background: #f9f9f9;
            border-radius: 5px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        button, .button {
            background-color: #4CAF50;
            border: none;
            color: white;
            padding: 10px 15px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 4px;
        }
        .button-secondary {
            background-color: #2196F3;
        }
        .button-warning {
            background-color: #ff9800;
        }
        input, select, textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-sizing: border-box;
            margin-top: 6px;
            margin-bottom: 16px;
            resize: vertical;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            font-weight: bold;
        }
    </style>
</head>
<body>
    <h1>Media Cleanup für Jellyfin</h1>
    
    <div class="card">
        <h2>Übersicht</h2>
        <div id="summary">
            <p>Gesamtzahl Filme: {{ stats.anzahl_filme if stats else 'Keine Daten' }}</p>
            <p>Gesamtgröße: {{ stats.gesamtgröße if stats else 'Keine Daten' }}</p>
            <p>Zuletzt gescannt: {{ stats.letzter_scan if stats else 'Noch nie' }}</p>
            <p>Identifizierte alte Filme: {{ stats.alte_filme if stats else '0' }}</p>
            <p>Ausgeführte Aktionen: {{ stats.aktionen if stats else '0' }}</p>
        </div>
        <button onclick="location.href='/start-scan'" class="button">Scan jetzt starten</button>
        <button onclick="location.href='/reports'" class="button button-secondary">Berichte ansehen</button>
    </div>
    
    <div class="card">
        <h2>Konfiguration</h2>
        <form action="/save-config" method="post">
            <div class="form-group">
                <label for="film_alter_tage">Film-Alter (Tage):</label>
                <input type="number" id="film_alter_tage" name="film_alter_tage" value="{{ config.film_alter_tage }}">
                <p><small>Filme älter als dieser Wert werden berücksichtigt.</small></p>
            </div>
            
            <div class="form-group">
                <label for="nicht_abgespielt_tage">Nicht abgespielt (Tage):</label>
                <input type="number" id="nicht_abgespielt_tage" name="nicht_abgespielt_tage" value="{{ config.nicht_abgespielt_tage }}">
                <p><small>Filme, die länger als dieser Zeitraum nicht abgespielt wurden, werden berücksichtigt.</small></p>
            </div>
            
            <div class="form-group">
                <label for="aktion">Aktion:</label>
                <select id="aktion" name="aktion">
                    <option value="bericht" {{ 'selected' if config.aktion == 'bericht' else '' }}>Nur Bericht erstellen</option>
                    <option value="verschieben" {{ 'selected' if config.aktion == 'verschieben' else '' }}>In Archiv verschieben</option>
                    <option value="löschen" {{ 'selected' if config.aktion == 'löschen' else '' }}>Löschen</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="jellyfin_url">Jellyfin URL:</label>
                <input type="text" id="jellyfin_url" name="jellyfin_url" value="{{ config.jellyfin_url }}">
                <p><small>z.B. http://jellyfin:8096</small></p>
            </div>
            
            <div class="form-group">
                <label for="jellyfin_api_key">Jellyfin API-Key:</label>
                <input type="password" id="jellyfin_api_key" name="jellyfin_api_key" value="{{ config.jellyfin_api_key }}">
            </div>
            
            <div class="form-group">
                <label for="film_ordner">Film-Ordner:</label>
                <input type="text" id="film_ordner" name="film_ordner" value="{{ config.film_ordner }}">
            </div>
            
            <div class="form-group">
                <label for="ausgabe_ordner">Ausgabe-Ordner:</label>
                <input type="text" id="ausgabe_ordner" name="ausgabe_ordner" value="{{ config.ausgabe_ordner }}">
            </div>
            
            <div class="form-group">
                <label for="ausnahmen">Ausnahmen (ein Pfad pro Zeile):</label>
                <textarea id="ausnahmen" name="ausnahmen" rows="5">{{ '\n'.join(config.ausnahmen) }}</textarea>
                <p><small>Filme, die diese Zeichenfolgen im Pfad enthalten, werden ignoriert.</small></p>
            </div>
            
            <div class="form-group">
                <label for="log_level">Log-Level:</label>
                <select id="log_level" name="log_level">
                    <option value="DEBUG" {{ 'selected' if config.log_level == 'DEBUG' else '' }}>DEBUG</option>
                    <option value="INFO" {{ 'selected' if config.log_level == 'INFO' else '' }}>INFO</option>
                    <option value="WARNING" {{ 'selected' if config.log_level == 'WARNING' else '' }}>WARNING</option>
                    <option value="ERROR" {{ 'selected' if config.log_level == 'ERROR' else '' }}>ERROR</option>
                </select>
            </div>
            
            <button type="submit" class="button">Konfiguration speichern</button>
            <button type="reset" class="button button-warning">Zurücksetzen</button>
        </form>
    </div>
    
    <div class="card">
        <h2>Neueste Filme</h2>
        <table>
            <thead>
                <tr>
                    <th>Dateiname</th>
                    <th>Erstellt am</th>
                    <th>Letzte Wiedergabe</th>
                    <th>Größe</th>
                </tr>
            </thead>
            <tbody>
                {% for film in filme %}
                <tr>
                    <td>{{ film.dateiname }}</td>
                    <td>{{ film.erstellungsdatum }}</td>
                    <td>{{ film.letzte_wiedergabe or 'Nie' }}</td>
                    <td>{{ film.größe }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <button onclick="location.href='/films'" class="button button-secondary">Alle Filme anzeigen</button>
    </div>
</body>
</html>
"""

FILMS_TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Film-Liste - Media Cleanup für Jellyfin</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }
        h1, h2 {
            color: #333;
        }
        .card {
            background: #f9f9f9;
            border-radius: 5px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        button, .button {
            background-color: #4CAF50;
            border: none;
            color: white;
            padding: 10px 15px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 4px;
        }
        .button-secondary {
            background-color: #2196F3;
        }
        .pagination {
            display: flex;
            justify-content: center;
            margin: 20px 0;
        }
        .pagination a {
            color: black;
            float: left;
            padding: 8px 16px;
            text-decoration: none;
            transition: background-color .3s;
            border: 1px solid #ddd;
            margin: 0 4px;
        }
        .pagination a.active {
            background-color: #4CAF50;
            color: white;
            border: 1px solid #4CAF50;
        }
        .pagination a:hover:not(.active) {
            background-color: #ddd;
        }
    </style>
</head>
<body>
    <h1>Film-Liste</h1>
    <button onclick="location.href='/'" class="button">Zurück zur Übersicht</button>
    
    <div class="card">
        <h2>Alle Filme</h2>
        <table>
            <thead>
                <tr>
                    <th>Dateiname</th>
                    <th>Erstellt am</th>
                    <th>Letzte Wiedergabe</th>
                    <th>Größe</th>
                    <th>Format</th>
                    <th>Auflösung</th>
                </tr>
            </thead>
            <tbody>
                {% for film in filme %}
                <tr>
                    <td>{{ film.dateiname }}</td>
                    <td>{{ film.erstellungsdatum }}</td>
                    <td>{{ film.letzte_wiedergabe or 'Nie' }}</td>
                    <td>{{ film.größe }}</td>
                    <td>{{ film.format or 'Unbekannt' }}</td>
                    <td>{{ film.auflösung or 'Unbekannt' }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        
        <div class="pagination">
            {% for i in range(1, seiten + 1) %}
                <a href="/films?page={{ i }}" class="{{ 'active' if i == seite else '' }}">{{ i }}</a>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

REPORTS_TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Berichte - Media Cleanup für Jellyfin</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }
        h1, h2 {
            color: #333;
        }
        .card {
            background: #f9f9f9;
            border-radius: 5px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        ul {
            list-style-type: none;
            padding: 0;
        }
        li {
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }
        li:last-child {
            border-bottom: none;
        }
        li:hover {
            background-color: #f5f5f5;
        }
        button, .button {
            background-color: #4CAF50;
            border: none;
            color: white;
            padding: 10px 15px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 4px;
        }
        a {
            text-decoration: none;
            color: #2196F3;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <h1>Berichte</h1>
    <button onclick="location.href='/'" class="button">Zurück zur Übersicht</button>
    
    <div class="card">
        <h2>Verfügbare Berichte</h2>
        {% if reports %}
            <ul>
                {% for report in reports %}
                    <li>
                        <a href="/reports/{{ report }}">{{ report }}</a>
                    </li>
                {% endfor %}
            </ul>
        {% else %}
            <p>Keine Berichte verfügbar.</p>
        {% endif %}
    </div>
    
    <div class="card">
        <h2>Statistik-Verlauf</h2>
        <table>
            <thead>
                <tr>
                    <th>Datum</th>
                    <th>Filme gesamt</th>
                    <th>Alte Filme</th>
                    <th>Nicht abgespielt</th>
                    <th>Aktionen</th>
                </tr>
            </thead>
            <tbody>
                {% for stat in stats %}
                <tr>
                    <td>{{ stat.scan_datum }}</td>
                    <td>{{ stat.anzahl_filme }}</td>
                    <td>{{ stat.alte_filme }}</td>
                    <td>{{ stat.nicht_abgespielte_filme }}</td>
                    <td>{{ stat.aktionen_ausgeführt }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

def get_db_connection():
    """Stellt eine Verbindung zur SQLite-Datenbank her."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def load_config():
    """Lädt die Konfiguration aus der JSON-Datei."""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        app.logger.error(f"Fehler beim Laden der Konfiguration: {e}")
        return {
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

def format_size(size_bytes):
    """Formatiert die Größe in ein lesbares Format."""
    if not size_bytes:
        return "Unbekannt"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def get_latest_stats():
    """Holt die neuesten Statistiken aus der Datenbank."""
    conn = get_db_connection()
    stats = conn.execute('SELECT * FROM statistiken ORDER BY id DESC LIMIT 1').fetchone()
    conn.close()
    
    if stats:
        return {
            "anzahl_filme": stats['anzahl_filme'],
            "gesamtgröße": format_size(stats['gesamtgröße_bytes']),
            "letzter_scan": stats['scan_datum'].split('T')[0],
            "alte_filme": stats['alte_filme'],
            "aktionen": stats['aktionen_ausgeführt']
        }
    return None

def get_newest_films(limit=10):
    """Holt die neuesten Filme aus der Datenbank."""
    conn = get_db_connection()
    films = conn.execute('''
        SELECT id, dateiname, erstellungsdatum, letzte_wiedergabe, größe_bytes 
        FROM filme 
        ORDER BY erstellungsdatum DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()
    
    result = []
    for film in films:
        result.append({
            "id": film['id'],
            "dateiname": film['dateiname'],
            "erstellungsdatum": film['erstellungsdatum'].split('T')[0],
            "letzte_wiedergabe": film['letzte_wiedergabe'].split('T')[0] if film['letzte_wiedergabe'] else None,
            "größe": format_size(film['größe_bytes'])
        })
    
    return result

@app.route('/')
def index():
    """Zeigt die Hauptseite an."""
    config = load_config()
    stats = get_latest_stats()
    films = get_newest_films(10)
    
    # Template mit den Daten rendern
    return INDEX_TEMPLATE.format(
        config=config,
        stats=stats,
        filme=films
    )

@app.route('/films')
def films():
    """Zeigt alle Filme an."""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page
    
    conn = get_db_connection()
    total = conn.execute('SELECT COUNT(*) FROM filme').fetchone()[0]
    films = conn.execute('''
        SELECT dateiname, erstellungsdatum, letzte_wiedergabe, größe_bytes, format, auflösung 
        FROM filme 
        ORDER BY erstellungsdatum DESC
        LIMIT ? OFFSET ?
    ''', (per_page, offset)).fetchall()
    conn.close()
    
    result = []
    for film in films:
        result.append({
            "dateiname": film['dateiname'],
            "erstellungsdatum": film['erstellungsdatum'].split('T')[0],
            "letzte_wiedergabe": film['letzte_wiedergabe'].split('T')[0] if film['letzte_wiedergabe'] else None,
            "größe": format_size(film['größe_bytes']),
            "format": film['format'],
            "auflösung": film['auflösung']
        })
    
    pages = (total + per_page - 1) // per_page
    
    # Template mit den Daten rendern
    return FILMS_TEMPLATE.format(
        filme=result,
        seite=page,
        seiten=pages
    )

@app.route('/reports')
def reports():
    """Zeigt die verfügbaren Berichte an."""
    config = load_config()
    ausgabe_ordner = config.get('ausgabe_ordner', '/output')
    
    # Berichte im Ausgabeordner suchen
    report_files = []
    if os.path.exists(ausgabe_ordner):
        for file in os.listdir(ausgabe_ordner):
            if file.startswith('alte_filme_') and file.endswith('.txt'):
                report_files.append(file)
    
    # Nach Datum sortieren (neueste zuerst)
    report_files.sort(reverse=True)
    
    # Statistiken holen
    conn = get_db_connection()
    stats = conn.execute('SELECT * FROM statistiken ORDER BY id DESC LIMIT 10').fetchall()
    conn.close()
    
    stats_list = []
    for stat in stats:
        stats_list.append({
            "scan_datum": stat['scan_datum'].split('T')[0],
            "anzahl_filme": stat['anzahl_filme'],
            "alte_filme": stat['alte_filme'],
            "nicht_abgespielte_filme": stat['nicht_abgespielte_filme'],
            "aktionen_ausgeführt": stat['aktionen_ausgeführt']
        })
    
    # Template mit den Daten rendern
    return REPORTS_TEMPLATE.format(
        reports=report_files,
        stats=stats_list
    )

@app.route('/reports/<filename>')
def download_report(filename):
    """Lädt einen Bericht herunter."""
    config = load_config()
    ausgabe_ordner = config.get('ausgabe_ordner', '/output')
    return send_from_directory(ausgabe_ordner, filename, as_attachment=True)

@app.route('/save-config', methods=['POST'])
def save_config():
    """Speichert die Konfiguration."""
    try:
        # Aktuelle Konfiguration laden
        config = load_config()
        
        # Formulardaten auslesen
        config['film_alter_tage'] = int(request.form.get('film_alter_tage', 365))
        config['nicht_abgespielt_tage'] = int(request.form.get('nicht_abgespielt_tage', 180))
        config['aktion'] = request.form.get('aktion', 'bericht')
        config['jellyfin_url'] = request.form.get('jellyfin_url', '')
        
        # API-Key nur überschreiben, wenn nicht leer
        new_api_key = request.form.get('jellyfin_api_key', '')
        if new_api_key:
            config['jellyfin_api_key'] = new_api_key
        
        config['film_ordner'] = request.form.get('film_ordner', '/media/movies')
        config['ausgabe_ordner'] = request.form.get('ausgabe_ordner', '/output')
        config['log_level'] = request.form.get('log_level', 'INFO')
        
        # Ausnahmen verarbeiten (ein Eintrag pro Zeile)
        ausnahmen_text = request.form.get('ausnahmen', '')
        config['ausnahmen'] = [line.strip() for line in ausnahmen_text.splitlines() if line.strip()]
        
        # Konfiguration speichern
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Fehler beim Speichern der Konfiguration: {e}")
        return f"Fehler beim Speichern der Konfiguration: {e}", 500

@app.route('/start-scan')
def start_scan():
    """Startet den Film-Scan manuell."""
    try:
        import subprocess
        subprocess.Popen(["python", "/app/scan_films.py"])
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Fehler beim Starten des Scans: {e}")
        return f"Fehler beim Starten des Scans: {e}", 500

@app.template_filter('datetime')
def format_datetime(value, format='%Y-%m-%d'):
    """Formatiert ein ISO-Datum."""
    if not value:
        return ''
    try:
        date = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
        return date.strftime(format)
    except Exception:
        return value

if __name__ == '__main__':
    # Flask-App starten
    app.run(host='0.0.0.0', port=8080, debug=False)