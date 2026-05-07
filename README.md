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
├── app.py                           # Application principale Streamlit
├── db.py                            # Connexion SQLAlchemy + helpers SQL
├── etl_import_ok.py                 # ETL principal — import CSV → DB (version validée)
├── etl_import.py                    # ETL alternatif (par date de réservation)
├── etl_import_by_doc_date.py        # ETL alternatif (par date de document)
├── csv/
│   ├── Liste_Option_Facturable_ok.csv   # Source principale (export RoomingIT)
│   ├── liste_contact.csv                # Annuaire clients (Zone6 = catégorie tarifaire)
│   └── reconciliaton_nassima.csv        # Journal comptable double-entrée
├── analyze_discrepancy.py           # Analyse des écarts de données
├── check_september_2023.py          # Vérification données sept. 2023
├── test_app.py                      # Tests application
├── test_corrected_logic.py          # Tests logique métier
├── requirements.txt                 # Dépendances Python
├── .env                             # Variables d'environnement (non versionné)
├── .env.example                     # Modèle de configuration
├── resaca.db                        # Base SQLite (non versionné)
├── REGLES_CALCUL.md                 # Règles de calcul CA validées
└── DEPLOYMENT.MD                    # Guide déploiement (Nginx, SSL, systemd)
```

---

## Installation

```bash
# 1. Configurer l'environnement
cp .env.example .env

# 2. Créer le virtualenv et installer les dépendances
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. Placer le CSV source dans csv/
#    → csv/Liste_Option_Facturable_ok.csv

# 4. Importer les données en base
.venv/bin/python etl_import_ok.py

# 5. Lancer l'application
.venv/bin/streamlit run app.py
```

L'app est accessible sur http://localhost:8501

---

## Configuration (`.env`)

```env
DATABASE_URL=sqlite:///./resaca.db
```

Pour PostgreSQL : `DATABASE_URL=postgresql://user:password@host/dbname`

---

## Logique comptable

Voir [`REGLES_CALCUL.md`](./REGLES_CALCUL.md) pour le détail complet des règles de calcul du CA, la structure des données, et les cas particuliers.

Résumé :
- **CA Brut** = Σ Factures − Σ Avoirs (filtrés par `reservation_date`)
- **CA Net** = Σ Factures dont `status = 'Encaissée'` (filtrées par `reservation_date`)
- **Écart** = CA Brut − CA Net (montant facturé non encore encaissé)

---

## Déploiement en production

Voir [`DEPLOYMENT.MD`](./DEPLOYMENT.MD) pour le guide complet (Nginx, SSL Let's Encrypt, service systemd).

```bash
# Mise à jour depuis GitHub
cd /var/www/html/stat-ageca
sudo git pull origin main
sudo systemctl restart stat-ageca
```
