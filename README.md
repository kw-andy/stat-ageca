# AGECA Dashboard

This project provides a simple pipeline to load reservation data from a CSV file into a database,  
and display analytics (reservations, CA brut, CA net) through an interactive dashboard.

---

## Order of operations

### 1. Run etl_import.py once


```bash
python etl_import.py
```

- Creates the database (`resaca.db` for SQLite).
- Creates the table `line_items`.
- Imports your CSV.

### 2. Run the app

```bash
python app.py
```

- Reads from the database created above.
- Builds the dashboard / charts.
- You can restart it any time; it always queries the existing DB.

### Note : Don't run db.py alone

It’s just a library module. It gets imported by `app.py`.