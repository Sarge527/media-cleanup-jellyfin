#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
import logging

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('init_db')

def init_database():
    """Initialisiert die SQLite-Datenbank mit den notwendigen Tabellen."""
    db_path = os.environ.get('DATABASE_PATH', '/config/database.sqlite')
    
    logger.info(f"Initialisiere Datenbank unter {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Film-Tabelle erstellen
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS filme (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pfad TEXT UNIQUE NOT NULL,
        dateiname TEXT NOT NULL,
        erstellungsdatum TEXT NOT NULL,
        letzte_wiedergabe TEXT,
        größe_bytes INTEGER NOT NULL,
        dauer_sekunden INTEGER,
        format TEXT,
        auflösung TEXT,
        zuletzt_geprüft TEXT NOT NULL
    )
    ''')
    
    # Verlaufs-Tabelle für Aktionen
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS aktionsverlauf (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        film_id INTEGER,
        aktion TEXT NOT NULL,
        zeitpunkt TEXT NOT NULL,
        details TEXT,
        FOREIGN KEY (film_id) REFERENCES filme (id)
    )
    ''')
    
    # Tabelle für Statistiken
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS statistiken (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_datum TEXT NOT NULL,
        anzahl_filme INTEGER NOT NULL,
        gesamtgröße_bytes INTEGER NOT NULL,
        identifizierte_filme INTEGER NOT NULL,
        alte_filme INTEGER NOT NULL,
        nicht_abgespielte_filme INTEGER NOT NULL,
        aktionen_ausgeführt INTEGER NOT NULL
    )
    ''')
    
    conn.commit()
    conn.close()
    
    logger.info("Datenbank erfolgreich initialisiert.")

if __name__ == "__main__":
    init_database()