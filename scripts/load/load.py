"""
Étape 3 – Chargement dans la base de données SQLite
Schéma : villes → mesures_horaires → agregats_journaliers
"""

import os
import sqlite3
import pandas as pd

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "../../data/processed")
DB_DIR = os.path.join(os.path.dirname(__file__), "../../database")
DB_PATH = os.path.join(DB_DIR, "climat_france.db")

SQL_CREATE = """
-- Table des villes
CREATE TABLE IF NOT EXISTS villes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT    NOT NULL UNIQUE,
    latitude    REAL    NOT NULL,
    longitude   REAL    NOT NULL,
    elevation   REAL,
    timezone    TEXT
);

-- Table des mesures horaires
CREATE TABLE IF NOT EXISTS mesures_horaires (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    ville_id                INTEGER NOT NULL,
    datetime                TEXT    NOT NULL,
    temperature_2m          REAL,
    humidite_relative       REAL,
    precipitations          REAL,
    pression_surface        REAL,
    temperature_ressentie   REAL,
    proba_precipitations    REAL,
    saison                  TEXT,
    tranche_horaire         TEXT,
    confort_thermique       TEXT,
    pluie                   INTEGER,
    FOREIGN KEY (ville_id) REFERENCES villes(id),
    UNIQUE (ville_id, datetime)
);

-- Table des agrégats journaliers
CREATE TABLE IF NOT EXISTS agregats_journaliers (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    ville_id                INTEGER NOT NULL,
    date                    TEXT    NOT NULL,
    annee                   INTEGER,
    mois                    INTEGER,
    temp_min                REAL,
    temp_max                REAL,
    temp_moy                REAL,
    humidite_moy            REAL,
    precipitations_totales  REAL,
    pression_moy            REAL,
    heures_pluie            INTEGER,
    FOREIGN KEY (ville_id) REFERENCES villes(id),
    UNIQUE (ville_id, date)
);
"""

VILLES_META = {
    "Paris":     {"latitude": 48.86, "longitude": 2.34,  "elevation": 43.0,  "timezone": "Europe/Paris"},
    "Marseille": {"latitude": 43.30, "longitude": 5.38,  "elevation": 30.0,  "timezone": "Europe/Paris"},
    "Lyon":      {"latitude": 45.74, "longitude": 4.84,  "elevation": 176.0, "timezone": "Europe/Paris"},
    "Nice":      {"latitude": 43.70, "longitude": 7.26,  "elevation": 17.0,  "timezone": "Europe/Paris"},
    "Toulouse":  {"latitude": 43.60, "longitude": 1.44,  "elevation": 149.0, "timezone": "Europe/Paris"},
}


def initialiser_db(conn: sqlite3.Connection):
    conn.executescript(SQL_CREATE)
    conn.commit()
    print("[LOAD] Schéma créé / vérifié.")


def inserer_villes(conn: sqlite3.Connection) -> dict:
    """Insère les villes et retourne un mapping nom → id."""
    cursor = conn.cursor()
    mapping = {}
    for nom, meta in VILLES_META.items():
        cursor.execute(
            "INSERT OR IGNORE INTO villes (nom, latitude, longitude, elevation, timezone) VALUES (?,?,?,?,?)",
            (nom, meta["latitude"], meta["longitude"], meta["elevation"], meta["timezone"]),
        )
        cursor.execute("SELECT id FROM villes WHERE nom = ?", (nom,))
        mapping[nom] = cursor.fetchone()[0]
    conn.commit()
    print(f"[LOAD] {len(mapping)} villes insérées / vérifiées.")
    return mapping


def charger_mesures_horaires(conn: sqlite3.Connection, mapping_villes: dict):
    chemin = os.path.join(PROCESSED_DIR, "donnees_propres.csv")
    df = pd.read_csv(chemin)
    df["ville_id"] = df["ville"].map(mapping_villes)
    df.dropna(subset=["ville_id"], inplace=True)
    df["ville_id"] = df["ville_id"].astype(int)

    cols = [
        "ville_id", "datetime", "temperature_2m", "humidite_relative",
        "precipitations", "pression_surface", "temperature_ressentie",
        "proba_precipitations", "saison", "tranche_horaire",
        "confort_thermique", "pluie",
    ]
    df_insert = df[[c for c in cols if c in df.columns]]

    cursor = conn.cursor()
    inserts = 0
    for _, row in df_insert.iterrows():
        try:
            cursor.execute(
                """INSERT OR IGNORE INTO mesures_horaires
                   (ville_id, datetime, temperature_2m, humidite_relative, precipitations,
                    pression_surface, temperature_ressentie, proba_precipitations,
                    saison, tranche_horaire, confort_thermique, pluie)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    row.get("ville_id"), row.get("datetime"), row.get("temperature_2m"),
                    row.get("humidite_relative"), row.get("precipitations"),
                    row.get("pression_surface"), row.get("temperature_ressentie"),
                    row.get("proba_precipitations"), row.get("saison"),
                    row.get("tranche_horaire"), row.get("confort_thermique"),
                    row.get("pluie"),
                ),
            )
            inserts += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    print(f"[LOAD] {inserts} mesures horaires insérées.")


def charger_agregats(conn: sqlite3.Connection, mapping_villes: dict):
    chemin = os.path.join(PROCESSED_DIR, "agregats_journaliers.csv")
    df = pd.read_csv(chemin)
    df["ville_id"] = df["ville"].map(mapping_villes)
    df.dropna(subset=["ville_id"], inplace=True)
    df["ville_id"] = df["ville_id"].astype(int)

    cursor = conn.cursor()
    inserts = 0
    for _, row in df.iterrows():
        try:
            cursor.execute(
                """INSERT OR IGNORE INTO agregats_journaliers
                   (ville_id, date, annee, mois, temp_min, temp_max, temp_moy,
                    humidite_moy, precipitations_totales, pression_moy, heures_pluie)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    int(row["ville_id"]), str(row["date"]), int(row["annee"]),
                    int(row["mois"]), row["temp_min"], row["temp_max"], row["temp_moy"],
                    row["humidite_moy"], row["precipitations_totales"],
                    row["pression_moy"], int(row["heures_pluie"]),
                ),
            )
            inserts += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    print(f"[LOAD] {inserts} agrégats journaliers insérés.")


def verifier_integrite(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM villes")
    print(f"[LOAD] Villes : {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM mesures_horaires")
    print(f"[LOAD] Mesures horaires : {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM agregats_journaliers")
    print(f"[LOAD] Agrégats journaliers : {cursor.fetchone()[0]}")
    cursor.execute("PRAGMA foreign_key_check")
    erreurs = cursor.fetchall()
    if erreurs:
        print(f"[LOAD] ⚠ Erreurs d'intégrité FK : {erreurs}")
    else:
        print("[LOAD] Intégrité des clés étrangères : OK")


if __name__ == "__main__":
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    initialiser_db(conn)
    mapping = inserer_villes(conn)
    charger_mesures_horaires(conn, mapping)
    charger_agregats(conn, mapping)
    verifier_integrite(conn)

    conn.close()
    print(f"[LOAD] Base de données disponible : {DB_PATH}")
