"""
Étape 2 – Transformation et nettoyage des données climatiques
"""

import os
import pandas as pd
import numpy as np

RAW_DIR = os.path.join(os.path.dirname(__file__), "../../data/raw")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "../../data/processed")


def charger_brut(nom_fichier: str = "donnees_brutes_csv.csv") -> pd.DataFrame:
    chemin = os.path.join(RAW_DIR, nom_fichier)
    df = pd.read_csv(chemin)
    print(f"[TRANSFORM] Chargement : {len(df)} lignes.")
    return df


def nettoyer(df: pd.DataFrame) -> pd.DataFrame:
    """Suppression des doublons, gestion des NaN, correction des types."""
    nb_avant = len(df)

    # Suppression des doublons
    df.drop_duplicates(subset=["ville", "datetime"], inplace=True)
    print(f"[TRANSFORM] Doublons supprimés : {nb_avant - len(df)}")

    # Conversion datetime
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df.dropna(subset=["datetime"], inplace=True)

    # Colonnes numériques attendues
    cols_num = [
        "temperature_2m", "humidite_relative", "precipitations",
        "pression_surface", "temperature_ressentie", "proba_precipitations",
    ]
    for col in cols_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Gestion des valeurs manquantes : interpolation linéaire par ville
    df.sort_values(["ville", "datetime"], inplace=True)
    for col in cols_num:
        if col in df.columns:
            df[col] = df.groupby("ville")[col].transform(
                lambda s: s.interpolate(method="linear", limit_direction="both")
            )

    nb_nan = df[cols_num].isna().sum().sum()
    print(f"[TRANSFORM] Valeurs manquantes restantes après interpolation : {nb_nan}")

    # Correction des valeurs aberrantes (ex : humidité > 100 %)
    if "humidite_relative" in df.columns:
        df["humidite_relative"] = df["humidite_relative"].clip(0, 100)
    if "precipitations" in df.columns:
        df["precipitations"] = df["precipitations"].clip(lower=0)
    if "proba_precipitations" in df.columns:
        df["proba_precipitations"] = df["proba_precipitations"].clip(0, 100)

    return df


def enrichir(df: pd.DataFrame) -> pd.DataFrame:
    """Ajout de colonnes dérivées utiles à l'analyse."""
    df["date"] = df["datetime"].dt.date
    df["heure"] = df["datetime"].dt.hour
    df["mois"] = df["datetime"].dt.month
    df["annee"] = df["datetime"].dt.year
    df["saison"] = df["mois"].map({
        12: "Hiver", 1: "Hiver", 2: "Hiver",
        3: "Printemps", 4: "Printemps", 5: "Printemps",
        6: "Été", 7: "Été", 8: "Été",
        9: "Automne", 10: "Automne", 11: "Automne",
    })

    # Tranche horaire
    bins = [-1, 5, 11, 17, 20, 23]
    labels = ["Nuit", "Matin", "Après-midi", "Soir", "Soirée"]
    df["tranche_horaire"] = pd.cut(df["heure"], bins=bins, labels=labels)

    # Ressenti thermique : confort
    df["confort_thermique"] = pd.cut(
        df["temperature_2m"],
        bins=[-np.inf, 0, 10, 20, 28, np.inf],
        labels=["Très froid", "Froid", "Frais", "Agréable", "Chaud"],
    )

    # Indicateur de pluie
    df["pluie"] = (df["precipitations"] > 0).astype(int)

    print(f"[TRANSFORM] Enrichissement : {len(df.columns)} colonnes au total.")
    return df


def sauvegarder_propre(df: pd.DataFrame, nom_fichier: str = "donnees_propres.csv"):
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    chemin = os.path.join(PROCESSED_DIR, nom_fichier)
    df.to_csv(chemin, index=False)
    print(f"[TRANSFORM] Données propres sauvegardées : {chemin}")


def generer_agregats_journaliers(df: pd.DataFrame) -> pd.DataFrame:
    """Agrège les mesures horaires en statistiques journalières par ville."""
    agg = df.groupby(["ville", "date"]).agg(
        temp_min=("temperature_2m", "min"),
        temp_max=("temperature_2m", "max"),
        temp_moy=("temperature_2m", "mean"),
        humidite_moy=("humidite_relative", "mean"),
        precipitations_totales=("precipitations", "sum"),
        pression_moy=("pression_surface", "mean"),
        heures_pluie=("pluie", "sum"),
    ).reset_index()
    agg["date"] = pd.to_datetime(agg["date"])
    agg["mois"] = agg["date"].dt.month
    agg["annee"] = agg["date"].dt.year
    return agg


if __name__ == "__main__":
    df = charger_brut()
    df = nettoyer(df)
    df = enrichir(df)
    sauvegarder_propre(df, "donnees_propres.csv")

    df_jour = generer_agregats_journaliers(df)
    sauvegarder_propre(df_jour, "agregats_journaliers.csv")

    print(f"[TRANSFORM] Transformation terminée. {len(df)} lignes traitées.")
