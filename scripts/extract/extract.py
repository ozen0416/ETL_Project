"""
Étape 1 – Extraction des données climatiques
Sources :
  - Fichier CSV local : données Open-Meteo (déjà collectées)
  - API Open-Meteo   : enrichissement / mise à jour pour d'autres villes
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta

RAW_DIR = os.path.join(os.path.dirname(__file__), "../../data/raw")

# Villes françaises couvertes
VILLES = {
    "Paris":     {"latitude": 48.86, "longitude": 2.34},
    "Marseille": {"latitude": 43.30, "longitude": 5.38},
    "Lyon":      {"latitude": 45.74, "longitude": 4.84},
    "Nice":      {"latitude": 43.70, "longitude": 7.26},
    "Toulouse":  {"latitude": 43.60, "longitude": 1.44},
}

VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "surface_pressure",
    "apparent_temperature",
    "precipitation_probability",
]


def extraire_depuis_csv(chemin_csv: str) -> pd.DataFrame:
    """Charge le fichier CSV brut Open-Meteo (format double-header)."""
    # Ligne 1-5 : métadonnées des localisations
    meta = pd.read_csv(chemin_csv, nrows=5)

    # Correspondance location_id → nom de ville
    coords_villes = {
        (48.86, 2.34): "Paris",
        (43.30, 5.38): "Marseille",
        (45.74, 4.84): "Lyon",
        (43.70, 7.26): "Nice",
        (43.60, 1.44): "Toulouse",
    }
    mapping_id_ville = {}
    for _, row in meta.iterrows():
        key = (round(float(row["latitude"]), 2), round(float(row["longitude"]), 2))
        mapping_id_ville[int(row["location_id"])] = coords_villes.get(key, f"Ville_{int(row['location_id'])}")

    # Les données horaires commencent après la ligne vide (ligne 7 dans le fichier)
    df = pd.read_csv(chemin_csv, skiprows=7)
    df.columns = [
        "location_id", "datetime", "temperature_2m", "humidite_relative",
        "precipitations", "pression_surface", "temperature_ressentie",
        "proba_precipitations",
    ]
    df["ville"] = df["location_id"].map(mapping_id_ville)
    print(f"[EXTRACT] CSV chargé : {len(df)} lignes, {df['ville'].nunique()} villes.")
    return df


def extraire_depuis_api(ville: str, latitude: float, longitude: float,
                        date_debut: str, date_fin: str) -> pd.DataFrame:
    """Appelle l'API Open-Meteo pour une ville et une plage de dates."""
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": date_debut,
        "end_date": date_fin,
        "hourly": ",".join(VARIABLES),
        "timezone": "Europe/Paris",
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    heures = data["hourly"]["time"]
    df = pd.DataFrame({"datetime": heures})
    for var in VARIABLES:
        df[var] = data["hourly"].get(var)

    df.rename(columns={
        "relative_humidity_2m": "humidite_relative",
        "precipitation": "precipitations",
        "surface_pressure": "pression_surface",
        "apparent_temperature": "temperature_ressentie",
        "precipitation_probability": "proba_precipitations",
    }, inplace=True)
    df["ville"] = ville
    print(f"[EXTRACT] API → {ville} : {len(df)} lignes récupérées.")
    return df


def sauvegarder_brut(df: pd.DataFrame, nom_fichier: str):
    os.makedirs(RAW_DIR, exist_ok=True)
    chemin = os.path.join(RAW_DIR, nom_fichier)
    df.to_csv(chemin, index=False)
    print(f"[EXTRACT] Données brutes sauvegardées : {chemin}")


if __name__ == "__main__":
    # --- Source 1 : fichier CSV déjà collecté ---
    csv_path = os.path.join(RAW_DIR, "open-meteo-france-villes.csv")
    df_csv = extraire_depuis_csv(csv_path)
    sauvegarder_brut(df_csv, "donnees_brutes_csv.csv")

    # --- Source 2 (optionnel) : enrichissement via API pour une période récente ---
    # Décommenter pour récupérer des données supplémentaires
    # date_fin = datetime.today().strftime("%Y-%m-%d")
    # date_debut = (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    # frames = []
    # for nom, coords in VILLES.items():
    #     df_api = extraire_depuis_api(nom, coords["latitude"], coords["longitude"],
    #                                  date_debut, date_fin)
    #     frames.append(df_api)
    # df_api_all = pd.concat(frames, ignore_index=True)
    # sauvegarder_brut(df_api_all, "donnees_brutes_api.csv")

    print("[EXTRACT] Extraction terminée.")
