#!/usr/bin/env python3
"""
Script to check September 2023 data from the database
"""
import pandas as pd
from db import fetch_dataframe, month_expr
from datetime import datetime

# Define September 2023 date range
date_debut = datetime(2023, 9, 1).date()
date_fin = datetime(2023, 10, 1).date()  # October 1st (exclusive)

print("=== September 2023 Analysis ===")
print(f"Period: {date_debut} to {date_fin} (exclusive)")
print()

# Query for CA data (same as in app.py)
print("1. CA Data Query:")
print("=================")

# Build parameters for CA query
params_ca = {"d1": date_debut, "d2": date_fin}

# CA query (same as in fetch_data function)
m_doc = month_expr("doc_date")
sql_ca = f"""
    SELECT {m_doc} AS mois,
           SUM(CASE WHEN NOT (doc_type LIKE 'Avoir%') THEN price_ttc*quantity ELSE 0 END) AS ca_brut,
           SUM(CASE WHEN (doc_type LIKE 'Avoir%')
                    THEN -price_ttc*quantity ELSE price_ttc*quantity END) AS ca_net
    FROM line_items
    WHERE doc_date >= :d1 AND doc_date < :d2
    GROUP BY 1
    ORDER BY 1
"""

print("SQL Query:")
print(sql_ca)
print()

try:
    df_ca = fetch_dataframe(sql_ca, params_ca)
    print("CA Results:")
    print(df_ca)
    print()

    if not df_ca.empty:
        ca_brut = df_ca['ca_brut'].iloc[0]
        ca_net = df_ca['ca_net'].iloc[0]
        print(f"CA Brut (Facturée): {ca_brut:,.0f}")
        print(f"CA Net (Encaissée): {ca_net:,.0f}")
        print()

        # Compare with accounting figures
        accounting_facturee = 37949
        accounting_encaissee = 32064

        print("=== COMPARISON WITH ACCOUNTING ===")
        print(f"Accounting Facturée: {accounting_facturee:,}")
        print(f"System CA Brut:      {ca_brut:,.0f}")
        print(f"Difference:          {ca_brut - accounting_facturee:+,.0f}")
        print()
        print(f"Accounting Encaissée: {accounting_encaissee:,}")
        print(f"System CA Net:        {ca_net:,.0f}")
        print(f"Difference:           {ca_net - accounting_encaissee:+,.0f}")
        print()

    else:
        print("No CA data found for September 2023")
        print()

except Exception as e:
    print(f"Error querying CA data: {e}")
    print()

# Query for reservations data
print("2. Reservations Data Query:")
print("===========================")

params_resa = {"r1": date_debut, "r2": date_fin}

m_resa = month_expr("reservation_date")
sql_resa = f"""
    SELECT {m_resa} AS mois, COUNT(DISTINCT doc_number) AS nb_reservations
    FROM line_items
    WHERE reservation_date >= :r1 AND reservation_date < :r2
    GROUP BY 1
    ORDER BY 1
"""

print("SQL Query:")
print(sql_resa)
print()

try:
    df_resa = fetch_dataframe(sql_resa, params_resa)
    print("Reservations Results:")
    print(df_resa)
    print()

except Exception as e:
    print(f"Error querying reservations data: {e}")

# Let's also check what statuses are available
print("3. Available Document Types and Statuses:")
print("=========================================")

sql_statuses = """
    SELECT DISTINCT doc_type, status, COUNT(*) as count
    FROM line_items
    WHERE doc_date >= :d1 AND doc_date < :d2
    GROUP BY doc_type, status
    ORDER BY doc_type, status
"""

try:
    df_statuses = fetch_dataframe(sql_statuses, params_ca)
    print("Document Types and Statuses for September 2023:")
    print(df_statuses)
    print()

except Exception as e:
    print(f"Error querying statuses: {e}")

print("Analysis complete.")