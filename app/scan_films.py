#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
import sqlite3
import datetime
import shutil
from pathlib import Path
from dateutil.parser import parse as parse_date
from pymediainfo import MediaInfo
import requests

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('film_scanner')

class FilmScanner:
    def __init__(self):
        # Konfiguration laden
        self.config_path = os.environ.get('CONFIG_PATH', '/config/settings.json')
        self.db_path = os.environ.get('DATABASE_PATH', '/config/database.sqlite')
        self.load_config()
        
        # Verbindung zur Datenbank herstellen
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        # Jellyfin-Verbindung initialisieren (falls konfiguriert)
        self.jellyfin_url = self.config.get('jellyfin_url')
        self.jellyfin_api_key = self.config.get('jellyfin_api_key')
        
        if self.jellyfin_url and self.jellyfin_api_key:
            logger.info(f"Jellyfin-Konfiguration gefunden: {self.jellyfin_url}")
        else:
            logger.warning("Keine Jellyfin-Konfiguration gefunden. Wiedergabedaten werden nicht abgerufen.")
    
    def load_config(self):
        """Lädt die Konfiguration aus der JSON-Datei."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                
            # Log-Level setzen
            log_level = getattr(logging, self.config.get('log_level', 'INFO'))
            logger.setLevel(log_level)
            
            logger.info(f"Konfiguration geladen: {self.config_path}")
        except Exception as e:
            logger.error(f"Fehler beim Laden der Konfiguration: {e}")
            sys.exit(1)
    
    def scan_filme(self):
        """Scannt das Film-Verzeichnis und aktualisiert die Datenbank."""
        film_dir = self.config.get('film_ordner', '/media/movies')
        logger.info(f"Starte Scan des Film-Verzeichnisses: {film_dir}")
        
        jetzt = datetime.datetime.now().isoformat()
        anzahl_filme = 0
        gesamtgröße = 0
        identifizierte_filme = 0
        
        # Durchsuche das Verzeichnis nach Filmdateien
        for root, _, files in os.walk(film_dir):
            for file in files:
                if self._ist_filmdatei(file):
                    file_path = os.path.join(root, file)
                    
                    # Prüfen, ob der Film bereits in der Datenbank ist
                    self.cursor.execute("SELECT * FROM filme WHERE pfad = ?", (file_path,))
                    existing_film = self.cursor.fetchone()
                    
                    file_stats = os.stat(file_path)
                    file_size = file_stats.st_size
                    creation_date = datetime.datetime.fromtimestamp(file_stats.st_ctime).isoformat()
                    
                    # MediaInfo für den Film abrufen
                    media_info = self._get_media_info(file_path)
                    
                    if existing_film:
                        # Film aktualisieren
                        self.cursor.execute("""
                            UPDATE filme 
                            SET größe_bytes = ?, dauer_sekunden = ?, format = ?, 
                                auflösung = ?, zuletzt_geprüft = ?
                            WHERE pfad = ?
                        """, (
                            file_size, 
                            media_info.get('dauer_sekunden'),
                            media_info.get('format'),
                            media_info.get('auflösung'),
                            jetzt,
                            file_path
                        ))
                    else:
                        # Neuen Film einfügen
                        self.cursor.execute("""
                            INSERT INTO filme 
                            (pfad, dateiname, erstellungsdatum, größe_bytes, 
                             dauer_sekunden, format, auflösung, zuletzt_geprüft)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            file_path,
                            file,
                            creation_date,
                            file_size,
                            media_info.get('dauer_sekunden'),
                            media_info.get('format'),
                            media_info.get('auflösung'),
                            jetzt
                        ))
                    
                    # Letzte Wiedergabe aus Jellyfin abrufen, falls verfügbar
                    if self.jellyfin_url and self.jellyfin_api_key:
                        last_played = self._get_jellyfin_last_played(file_path)
                        if last_played:
                            self.cursor.execute("""
                                UPDATE filme SET letzte_wiedergabe = ? WHERE pfad = ?
                            """, (last_played, file_path))
                            identifizierte_filme += 1
                    
                    anzahl_filme += 1
                    gesamtgröße += file_size
                    
                    if anzahl_filme % 100 == 0:
                        logger.info(f"{anzahl_filme} Filme gescannt...")
                        self.conn.commit()
        
        # Änderungen speichern
        self.conn.commit()
        logger.info(f"Scan abgeschlossen. {anzahl_filme} Filme in der Datenbank.")
        
        # Alte Filme identifizieren und Aktionen ausführen
        alte_filme, nicht_abgespielte_filme, aktionen = self.verarbeite_alte_filme()
        
        # Statistiken speichern
        self._speichere_statistik(jetzt, anzahl_filme, gesamtgröße, identifizierte_filme, 
                                 alte_filme, nicht_abgespielte_filme, aktionen)
    
    def _ist_filmdatei(self, filename):
        """Prüft, ob es sich um eine Filmdatei handelt."""
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.m4v', '.flv', '.webm']
        return any(filename.lower().endswith(ext) for ext in video_extensions)
    
    def _get_media_info(self, file_path):
        """Extrahiert Medieninformationen aus der Datei."""
        try:
            media_info = MediaInfo.parse(file_path)
            result = {}
            
            for track in media_info.tracks:
                if track.track_type == 'General':
                    result['format'] = track.format
                    result['dauer_sekunden'] = int(float(track.duration) / 1000) if track.duration else None
                
                if track.track_type == 'Video':
                    if track.width and track.height:
                        result['auflösung'] = f"{track.width}x{track.height}"
            
            return result
        except Exception as e:
            logger.error(f"Fehler bei MediaInfo für {file_path}: {e}")
            return {}
    
    def _get_jellyfin_last_played(self, file_path):
        """Versucht, das letzte Wiedergabedatum aus Jellyfin zu ermitteln."""
        if not self.jellyfin_url or not self.jellyfin_api_key:
            return None
        
        try:
            # Normalisiere den Dateipfad für die Suche
            norm_path = os.path.basename(file_path)
            file_name_no_ext = os.path.splitext(norm_path)[0]
            
            # Suche nach dem Film in der Jellyfin-Bibliothek via API
            headers = {
                'X-Emby-Token': self.jellyfin_api_key
            }
            
            # Suche nach dem Film-Titel
            search_url = f"{self.jellyfin_url}/Items?SearchTerm={file_name_no_ext}&IncludeItemTypes=Movie&Recursive=true"
            response = requests.get(search_url, headers=headers)
            
            if response.status_code == 200:
                search_results = response.json()
                
                if search_results.get('TotalRecordCount', 0) > 0:
                    # Nimm das erste Ergebnis (am relevantesten)
                    movie = search_results['Items'][0]
                    movie_id = movie['Id']
                    
                    # Hole die Wiedergabedaten für diesen Film
                    playback_url = f"{self.jellyfin_url}/Users/{movie['UserId']}/Items/{movie_id}/PlaybackInfo"
                    playback_response = requests.get(playback_url, headers=headers)
                    
                    if playback_response.status_code == 200:
                        playback_info = playback_response.json()
                        
                        # Prüfe, ob der Film jemals abgespielt wurde
                        if playback_info.get('PlaybackPositionTicks', 0) > 0:
                            # Konvertiere das letzte Wiedergabedatum in ein ISO-Format
                            last_played = playback_info.get('LastPlayedDate')
                            if last_played:
                                return last_played
            
            return None
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Jellyfin-Wiedergabedatums für {file_path}: {e}")
            return None
    
    def verarbeite_alte_filme(self):
        """Identifiziert alte Filme und führt die konfigurierten Aktionen aus."""
        film_alter_tage = self.config.get('film_alter_tage', 365)
        nicht_abgespielt_tage = self.config.get('nicht_abgespielt_tage', 180)
        aktion = self.config.get('aktion', 'bericht')
        ausnahmen = self.config.get('ausnahmen', [])
        
        # Datum berechnen für alte Filme
        alter_datum = (datetime.datetime.now() - datetime.timedelta(days=film_alter_tage)).isoformat()
        
        # Datum berechnen für nicht abgespielte Filme
        nicht_abgespielt_datum = (datetime.datetime.now() - datetime.timedelta(days=nicht_abgespielt_tage)).isoformat()
        
        # Alte Filme identifizieren
        self.cursor.execute("""
            SELECT * FROM filme 
            WHERE erstellungsdatum < ? 
            AND (letzte_wiedergabe IS NULL OR letzte_wiedergabe < ?)
        """, (alter_datum, nicht_abgespielt_datum))
        
        alte_filme = self.cursor.fetchall()
        logger.info(f"Gefunden: {len(alte_filme)} alte Filme, die länger als {nicht_abgespielt_tage} Tage nicht abgespielt wurden.")
        
        # Aktionen ausführen
        ausgabe_ordner = self.config.get('ausgabe_ordner', '/output')
        os.makedirs(ausgabe_ordner, exist_ok=True)
        
        report_path = os.path.join(ausgabe_ordner, f"alte_filme_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        
        aktionen_ausgeführt = 0
        nicht_abgespielte_filme = 0
        
        with open(report_path, 'w', encoding='utf-8') as report:
            report.write(f"Bericht: Alte Filme (älter als {film_alter_tage} Tage) und länger als {nicht_abgespielt_tage} Tage nicht abgespielt\n")
            report.write("-" * 80 + "\n\n")
            
            for film in alte_filme:
                # Prüfe Ausnahmen
                skip = False
                for ausnahme in ausnahmen:
                    if ausnahme in film['pfad']:
                        logger.info(f"Film übersprungen (Ausnahme): {film['pfad']}")
                        skip = True
                        break
                
                if skip:
                    continue
                
                # Füge den Film zum Bericht hinzu
                report.write(f"Film: {film['dateiname']}\n")
                report.write(f"Pfad: {film['pfad']}\n")
                report.write(f"Erstellt am: {film['erstellungsdatum']}\n")
                report.write(f"Zuletzt abgespielt: {film['letzte_wiedergabe'] or 'Nie'}\n")
                report.write(f"Größe: {self._format_size(film['größe_bytes'])}\n")
                report.write(f"Dauer: {self._format_duration(film['dauer_sekunden'])}\n")
                report.write(f"Format: {film['format'] or 'Unbekannt'}\n")
                report.write(f"Auflösung: {film['auflösung'] or 'Unbekannt'}\n\n")
                
                nicht_abgespielte_filme += 1
                
                # Aktion ausführen
                if aktion == 'verschieben':
                    archiv_ordner = os.path.join(ausgabe_ordner, 'archiv')
                    os.makedirs(archiv_ordner, exist_ok=True)
                    
                    ziel_pfad = os.path.join(archiv_ordner, film['dateiname'])
                    try:
                        shutil.move(film['pfad'], ziel_pfad)
                        logger.info(f"Film verschoben: {film['pfad']} -> {ziel_pfad}")
                        
                        self.cursor.execute("""
                            INSERT INTO aktionsverlauf (film_id, aktion, zeitpunkt, details)
                            VALUES (?, ?, ?, ?)
                        """, (film['id'], 'verschieben', datetime.datetime.now().isoformat(), ziel_pfad))
                        
                        aktionen_ausgeführt += 1
                    except Exception as e:
                        logger.error(f"Fehler beim Verschieben des Films {film['pfad']}: {e}")
                
                elif aktion == 'löschen':
                    try:
                        os.remove(film['pfad'])
                        logger.info(f"Film gelöscht: {film['pfad']}")
                        
                        self.cursor.execute("""
                            INSERT INTO aktionsverlauf (film_id, aktion, zeitpunkt, details)
                            VALUES (?, ?, ?, ?)
                        """, (film['id'], 'löschen', datetime.datetime.now().isoformat(), None))
                        
                        aktionen_ausgeführt += 1
                    except Exception as e:
                        logger.error(f"Fehler beim Löschen des Films {film['pfad']}: {e}")
        
        # Änderungen speichern
        self.conn.commit()
        
        logger.info(f"Bericht erstellt: {report_path}")
        logger.info(f"Aktionen ausgeführt: {aktionen_ausgeführt}")
        
        return len(alte_filme), nicht_abgespielte_filme, aktionen_ausgeführt
    
    def _format_size(self, size_bytes):
        """Formatiert die Größe in ein lesbares Format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def _format_duration(self, seconds):
        """Formatiert die Dauer in ein lesbares Format."""
        if not seconds:
            return "Unbekannt"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def _speichere_statistik(self, scan_datum, anzahl_filme, gesamtgröße, identifizierte_filme, 
                           alte_filme, nicht_abgespielte_filme, aktionen_ausgeführt):
        """Speichert die Statistiken in der Datenbank."""
        self.cursor.execute("""
            INSERT INTO statistiken 
            (scan_datum, anzahl_filme, gesamtgröße_bytes, identifizierte_filme, 
             alte_filme, nicht_abgespielte_filme, aktionen_ausgeführt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            scan_datum, 
            anzahl_filme, 
            gesamtgröße, 
            identifizierte_filme, 
            alte_filme,
            nicht_abgespielte_filme,
            aktionen_ausgeführt
        ))
        
        self.conn.commit()
        logger.info("Statistiken gespeichert.")
    
    def cleanup(self):
        """Schließt Datenbankverbindungen und gibt Ressourcen frei."""
        if self.conn:
            self.conn.close()
            logger.info("Datenbankverbindung geschlossen.")

def main():
    scanner = FilmScanner()
    try:
        scanner.scan_filme()
    except Exception as e:
        logger.error(f"Fehler beim Ausführen des Film-Scanners: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        scanner.cleanup()

if __name__ == "__main__":
    main()