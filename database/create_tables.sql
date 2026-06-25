-- ============================================================
-- Schéma de la base de données : Climat France
-- Projet ETL M1 Data & IA – Ynov 2025-2026
-- ============================================================

-- Table de référence des villes
CREATE TABLE IF NOT EXISTS villes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT    NOT NULL UNIQUE,
    latitude    REAL    NOT NULL,
    longitude   REAL    NOT NULL,
    elevation   REAL,           -- Altitude en mètres
    timezone    TEXT            -- Ex : Europe/Paris
);

-- Mesures climatiques horaires
CREATE TABLE IF NOT EXISTS mesures_horaires (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    ville_id                INTEGER NOT NULL,
    datetime                TEXT    NOT NULL,   -- ISO 8601 : 2024-01-01T00:00
    temperature_2m          REAL,               -- °C
    humidite_relative       REAL,               -- %
    precipitations          REAL,               -- mm
    pression_surface        REAL,               -- hPa
    temperature_ressentie   REAL,               -- °C
    proba_precipitations    REAL,               -- %
    saison                  TEXT,               -- Hiver / Printemps / Été / Automne
    tranche_horaire         TEXT,               -- Nuit / Matin / Après-midi / Soir
    confort_thermique       TEXT,               -- Très froid / Froid / Frais / Agréable / Chaud
    pluie                   INTEGER,            -- 0 ou 1

    FOREIGN KEY (ville_id) REFERENCES villes(id),
    UNIQUE (ville_id, datetime)
);

-- Agrégats journaliers par ville
CREATE TABLE IF NOT EXISTS agregats_journaliers (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    ville_id                INTEGER NOT NULL,
    date                    TEXT    NOT NULL,   -- YYYY-MM-DD
    annee                   INTEGER,
    mois                    INTEGER,
    temp_min                REAL,               -- °C
    temp_max                REAL,               -- °C
    temp_moy                REAL,               -- °C
    humidite_moy            REAL,               -- %
    precipitations_totales  REAL,               -- mm (cumul journalier)
    pression_moy            REAL,               -- hPa
    heures_pluie            INTEGER,            -- Nombre d'heures avec pluie

    FOREIGN KEY (ville_id) REFERENCES villes(id),
    UNIQUE (ville_id, date)
);

-- Index pour accélérer les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_mh_ville_date    ON mesures_horaires (ville_id, datetime);
CREATE INDEX IF NOT EXISTS idx_mh_saison        ON mesures_horaires (saison);
CREATE INDEX IF NOT EXISTS idx_aj_ville_mois    ON agregats_journaliers (ville_id, mois);
