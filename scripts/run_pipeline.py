"""
Script principal : lance le pipeline ETL complet Extract → Transform → Load
Usage : python scripts/run_pipeline.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from extract.extract import extraire_depuis_csv, sauvegarder_brut
from transform.transform import charger_brut, nettoyer, enrichir, sauvegarder_propre, generer_agregats_journaliers
from load.load import initialiser_db, inserer_villes, charger_mesures_horaires, charger_agregats, verifier_integrite

import sqlite3

RAW_DIR = os.path.join(os.path.dirname(__file__), "../data/raw")
DB_DIR = os.path.join(os.path.dirname(__file__), "../database")
DB_PATH = os.path.join(DB_DIR, "climat_france.db")


def main():
    print("=" * 50)
    print("PIPELINE ETL – Climat France")
    print("=" * 50)

    # ÉTAPE 1 : EXTRACT
    print("\n[1/3] EXTRACTION")
    csv_path = os.path.join(RAW_DIR, "open-meteo-france-villes.csv")
    df_brut = extraire_depuis_csv(csv_path)
    sauvegarder_brut(df_brut, "donnees_brutes_csv.csv")

    # ÉTAPE 2 : TRANSFORM
    print("\n[2/3] TRANSFORMATION")
    df = charger_brut("donnees_brutes_csv.csv")
    df = nettoyer(df)
    df = enrichir(df)
    sauvegarder_propre(df, "donnees_propres.csv")

    df_jour = generer_agregats_journaliers(df)
    sauvegarder_propre(df_jour, "agregats_journaliers.csv")

    # ÉTAPE 3 : LOAD
    print("\n[3/3] CHARGEMENT EN BASE")
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    initialiser_db(conn)
    mapping = inserer_villes(conn)
    charger_mesures_horaires(conn, mapping)
    charger_agregats(conn, mapping)
    verifier_integrite(conn)
    conn.close()

    print("\n" + "=" * 50)
    print("Pipeline terminé avec succès.")
    print(f"Base de données : {DB_PATH}")
    print("=" * 50)


if __name__ == "__main__":
    main()
