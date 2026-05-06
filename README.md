# AGECA Dashboard

Dashboard analytique pour visualiser les réservations et le chiffre d'affaires (brut/net) par mois.

**URL** : https://stat.just-go.dev  
**Dépôt** : https://github.com/kw-andy/stat-ageca  
**Serveur** : `/var/www/html/stat-ageca`

---

## Stack

- [Streamlit](https://streamlit.io) — dashboard interactif
- [Plotly](https://plotly.com) — graphiques
- [SQLAlchemy](https://www.sqlalchemy.org) — accès base de données
- SQLite (`resaca.db`) ou PostgreSQL
- python-dotenv — configuration via `.env`

---

## Structure

```
stat-ageca/
├── app.py                        # Application principale Streamlit
├── db.py                         # Connexion SQLAlchemy + helpers SQL
├── etl_import.py                 # Import CSV → DB (par date de réservation)
├── etl_import_by_doc_date.py     # Import CSV → DB (par date de document)
├── analyze_discrepancy.py        # Analyse des écarts de données
├── check_september_2023.py       # Vérification données sept. 2023
├── test_app.py                   # Tests application
├── test_corrected_logic.py       # Tests logique métier
├── requirements.txt              # Dépendances Python
├── .env                          # Variables d'environnement (non versionné)
├── .env.example                  # Modèle de configuration
├── Liste_Option_Facturable.csv   # Source de données
├── resaca.db                     # Base SQLite
└── DEPLOYMENT.MD                 # Guide déploiement (Nginx, SSL, systemd)
```

---

## Installation

```bash
# 1. Configurer l'environnement
cp .env.example .env

# 2. Créer le virtualenv et installer les dépendances
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. Importer les données CSV en base (une seule fois)
.venv/bin/python etl_import.py

# 4. Lancer l'application
.venv/bin/streamlit run app.py
```

L'app est accessible sur http://localhost:8501

---

## Configuration (`.env`)

```env
DATABASE_URL=sqlite:///./resaca.db
CSV_PATH=./Liste_Option_Facturable.csv
```

Pour PostgreSQL : `DATABASE_URL=postgresql://user:password@host/dbname`

---

## Déploiement en production

Voir [`DEPLOYMENT.MD`](./DEPLOYMENT.MD) pour le guide complet (Nginx, SSL Let's Encrypt, service systemd).

```bash
# Mise à jour depuis GitHub
cd /var/www/html/stat-ageca
sudo git pull origin main
sudo systemctl restart stat-ageca
```
