# Projet ETL – Données Climatiques France
**Master Data & IA – M1 – Ynov 2025-2026**

---

## Sujet

Analyse climatique de 5 grandes villes françaises à partir de données horaires collectées depuis 2024.  
Les données proviennent de l'API **Open-Meteo** (open data, libre d'accès, sans clé).

**Villes couvertes :** Paris · Marseille · Lyon · Nice · Toulouse

**Variables mesurées :**
- Température à 2m (°C)
- Température ressentie (°C)
- Humidité relative (%)
- Précipitations (mm)
- Pression de surface (hPa)
- Probabilité de précipitations (%)

---

## Architecture du projet

```
ETL Project/
├── data/
│   ├── raw/                          # Données brutes (Extract)
│   │   ├── open-meteo-france-villes.csv   # Fichier source original
│   │   └── donnees_brutes_csv.csv         # Données après extraction
│   └── processed/                    # Données nettoyées (Transform)
│       ├── donnees_propres.csv            # Données horaires enrichies
│       └── agregats_journaliers.csv       # Statistiques journalières
├── scripts/
│   ├── extract/
│   │   └── extract.py                # Étape 1 : Extraction
│   ├── transform/
│   │   └── transform.py              # Étape 2 : Nettoyage & enrichissement
│   ├── load/
│   │   └── load.py                   # Étape 3 : Chargement en base
│   └── run_pipeline.py               # Script principal (lance les 3 étapes)
├── database/
│   ├── create_tables.sql             # Schéma SQL de la base
│   └── climat_france.db              # Base SQLite (générée)
├── notebooks/
│   └── exploration.ipynb             # Analyses exploratoires & visualisations
├── requirements/
│   └── requirements.txt              # Dépendances Python
└── README.md
```

---

## Installation

### Prérequis
- Python 3.10+
- pip

### Installer les dépendances

```bash
pip install -r requirements/requirements.txt
```

---

## Lancer le pipeline ETL complet

```bash
python scripts/run_pipeline.py
```

Cela exécute les 3 étapes dans l'ordre et affiche un rapport dans la console.

Il est aussi possible de lancer chaque étape séparément :

```bash
python scripts/extract/extract.py
python scripts/transform/transform.py
python scripts/load/load.py
```

---

## Étape 1 – Extraction

**Script :** `scripts/extract/extract.py`

### Source principale : fichier CSV Open-Meteo
Le fichier `data/raw/open-meteo-france-villes.csv` a été téléchargé manuellement depuis [open-meteo.com](https://open-meteo.com).  
Il contient des mesures **horaires depuis le 01/01/2024** pour 5 villes.

Structure du fichier CSV :
- **Lignes 1–5 :** métadonnées de localisation (latitude, longitude, altitude, fuseau horaire)
- **Ligne 6 :** vide (séparateur)
- **Ligne 7+ :** données horaires (location_id, datetime, variables météo)

### Source complémentaire : API Open-Meteo (optionnel)
Le script contient également une fonction `extraire_depuis_api()` permettant d'interroger l'API historique d'Open-Meteo pour n'importe quelle ville et plage de dates, sans clé d'authentification.

```python
# Décommenter dans extract.py pour enrichir avec l'API
extraire_depuis_api("Bordeaux", 44.84, -0.58, "2024-01-01", "2024-12-31")
```

### Résultat
- **87 720 lignes** extraites (5 villes × ~17 544 heures)
- Fichier de sortie : `data/raw/donnees_brutes_csv.csv`

---

## Étape 2 – Transformation

**Script :** `scripts/transform/transform.py`

### Nettoyage
| Opération | Détail |
|-----------|--------|
| Suppression des doublons | Sur les colonnes `(ville, datetime)` |
| Conversion des types | `datetime` → `pd.Timestamp`, numériques via `pd.to_numeric` |
| Gestion des valeurs manquantes | Interpolation linéaire par ville (`limit_direction="both"`) |
| Correction des aberrations | Humidité clippée entre 0 % et 100 %, précipitations ≥ 0 |

### Enrichissement (colonnes ajoutées)
| Colonne | Description |
|---------|-------------|
| `date` | Date seule extraite du datetime |
| `heure` | Heure (0–23) |
| `mois` | Mois (1–12) |
| `annee` | Année |
| `saison` | Hiver / Printemps / Été / Automne |
| `tranche_horaire` | Nuit / Matin / Après-midi / Soir / Soirée |
| `confort_thermique` | Très froid / Froid / Frais / Agréable / Chaud |
| `pluie` | 1 si précipitations > 0, sinon 0 |

### Agrégats journaliers
Un deuxième fichier `agregats_journaliers.csv` est généré avec les statistiques par ville et par jour :  
temp_min, temp_max, temp_moy, humidité moyenne, précipitations totales, pression moyenne, heures de pluie.

### Résultats
- 0 doublon détecté
- 0 valeur manquante après interpolation
- 17 colonnes au total dans `donnees_propres.csv`
- 3 655 lignes dans `agregats_journaliers.csv`

---

## Étape 3 – Chargement

**Script :** `scripts/load/load.py`  
**Schéma SQL :** `database/create_tables.sql`  
**Base de données :** `database/climat_france.db` (SQLite)

### Schéma relationnel

```
villes (id, nom, latitude, longitude, elevation, timezone)
  │
  ├──< mesures_horaires (id, ville_id, datetime, temperature_2m, humidite_relative,
  │                       precipitations, pression_surface, temperature_ressentie,
  │                       proba_precipitations, saison, tranche_horaire,
  │                       confort_thermique, pluie)
  │
  └──< agregats_journaliers (id, ville_id, date, annee, mois, temp_min, temp_max,
                              temp_moy, humidite_moy, precipitations_totales,
                              pression_moy, heures_pluie)
```

Les clés étrangères sont activées (`PRAGMA foreign_keys = ON`).  
Des contraintes `UNIQUE (ville_id, datetime)` évitent les doublons en base.

### Résultats
| Table | Lignes |
|-------|--------|
| `villes` | 5 |
| `mesures_horaires` | 87 720 |
| `agregats_journaliers` | 3 655 |
| Intégrité FK | OK |

---

## Exemples de requêtes SQL

```sql
-- Température moyenne par ville sur toute la période
SELECT v.nom, ROUND(AVG(m.temperature_2m), 2) AS temp_moy
FROM mesures_horaires m
JOIN villes v ON v.id = m.ville_id
GROUP BY v.nom
ORDER BY temp_moy DESC;

-- Jours les plus pluvieux à Paris
SELECT date, precipitations_totales
FROM agregats_journaliers a
JOIN villes v ON v.id = a.ville_id
WHERE v.nom = 'Paris'
ORDER BY precipitations_totales DESC
LIMIT 10;

-- Comparaison des températures estivales entre villes
SELECT v.nom, ROUND(AVG(m.temperature_2m), 2) AS temp_moy_ete
FROM mesures_horaires m
JOIN villes v ON v.id = m.ville_id
WHERE m.saison = 'Été'
GROUP BY v.nom
ORDER BY temp_moy_ete DESC;
```

---

## Exploration & Visualisations

Ouvrir le notebook :

```bash
jupyter notebook notebooks/exploration.ipynb
```

Visualisations disponibles :
1. Température moyenne mensuelle par ville (courbes)
2. Précipitations totales mensuelles par ville (barres)
3. Distribution des températures par saison (boxplots)
4. Heatmap température horaire × mois (Paris)

---

## Sources de données

| Source | Type | URL |
|--------|------|-----|
| Open-Meteo Historical API | API REST / CSV | https://open-meteo.com |

Open-Meteo est une API open source et libre d'accès, sans clé d'authentification requise.  
Les données sont issues de modèles météorologiques (ERA5, ECMWF) et sont disponibles depuis 1940.

---

## Livrables

- [x] Code source complet du pipeline ETL
- [x] Données brutes (`data/raw/`)
- [x] Données transformées (`data/processed/`)
- [x] Base de données SQLite (`database/climat_france.db`)
- [x] Documentation technique (ce fichier)
- [ ] Présentation finale – 07/07/2026

---

## Auteurs

Projet réalisé dans le cadre du Master Data & IA – M1 – Ynov 2025-2026.
