#!/usr/bin/env python3
"""
Test the corrected logic for September 2023
"""
import pandas as pd
from db import fetch_dataframe, month_expr
from datetime import datetime

# Define September 2023 date range
date_debut = datetime(2023, 9, 1).date()
date_fin = datetime(2023, 10, 1).date()

print("=== TESTING CORRECTED LOGIC FOR SEPTEMBER 2023 ===")
print(f"Period: {date_debut} to {date_fin} (exclusive)")
print()

# Test the new CA calculation logic
params = {"d1": date_debut, "d2": date_fin}

m_doc = month_expr("doc_date")
sql_ca_corrected = f"""
    SELECT {m_doc} AS mois,
           SUM(CASE WHEN doc_type = 'Facture' AND status = 'Facturée' THEN price_ttc*quantity ELSE 0 END) AS ca_brut,
           SUM(CASE WHEN doc_type = 'Facture' AND status = 'Encaissée' THEN price_ttc*quantity ELSE 0 END) AS ca_net
    FROM line_items
    WHERE doc_date >= :d1 AND doc_date < :d2
    GROUP BY 1
    ORDER BY 1
"""

print("1. NEW CORRECTED CA CALCULATION:")
print("="*35)
print("SQL Query:")
print(sql_ca_corrected)
print()

try:
    df_ca_corrected = fetch_dataframe(sql_ca_corrected, params)
    print("Results with corrected logic:")
    print(df_ca_corrected)
    print()

    if not df_ca_corrected.empty:
        ca_facturee = df_ca_corrected['ca_brut'].iloc[0]
        ca_encaissee = df_ca_corrected['ca_net'].iloc[0]
        ecart = ca_facturee - ca_encaissee

        print(f"CA Facturé (Facture + Facturée):  {ca_facturee:,.0f} €")
        print(f"CA Encaissé (Facture + Encaissée): {ca_encaissee:,.0f} €")
        print(f"Écart (Facturé - Encaissé):       {ecart:,.0f} €")
        print()

        # Compare with accounting
        accounting_facturee = 37949
        accounting_encaissee = 32064

        print("="*50)
        print("COMPARISON WITH ACCOUNTING FIGURES:")
        print("="*50)
        print(f"Accounting Facturée:  {accounting_facturee:8,} €")
        print(f"System Facturé:       {ca_facturee:8,.0f} €")
        print(f"Difference:           {ca_facturee - accounting_facturee:8+,.0f} €")
        print()
        print(f"Accounting Encaissée: {accounting_encaissee:8,} €")
        print(f"System Encaissé:      {ca_encaissee:8,.0f} €")
        print(f"Difference:           {ca_encaissee - accounting_encaissee:8+,.0f} €")
        print()

        # Calculate accuracy
        facture_accuracy = abs(ca_facturee - accounting_facturee) / accounting_facturee * 100
        encaisse_accuracy = abs(ca_encaissee - accounting_encaissee) / accounting_encaissee * 100

        print(f"Facturé accuracy:  {100 - facture_accuracy:5.1f}% match")
        print(f"Encaissé accuracy: {100 - encaisse_accuracy:5.1f}% match")
        print()

    else:
        print("No data found with corrected logic!")

except Exception as e:
    print(f"Error with corrected logic: {e}")

# Let's also break down by exact status to see what we have
print("2. DETAILED BREAKDOWN BY STATUS:")
print("="*35)

sql_breakdown = """
    SELECT
        doc_type,
        status,
        COUNT(DISTINCT doc_number) as doc_count,
        SUM(price_ttc * quantity) as total_amount
    FROM line_items
    WHERE doc_date >= :d1 AND doc_date < :d2
    AND doc_type = 'Facture'
    GROUP BY doc_type, status
    ORDER BY status
"""

try:
    df_breakdown = fetch_dataframe(sql_breakdown, params)
    print("Facture breakdown by status:")
    for _, row in df_breakdown.iterrows():
        print(f"  {row['status']:10s}: {row['doc_count']:3d} docs = {row['total_amount']:8,.0f} €")
    print()

    # Show the exact amounts we're now calculating
    facturee_amount = df_breakdown[df_breakdown['status'] == 'Facturée']['total_amount'].sum()
    encaissee_amount = df_breakdown[df_breakdown['status'] == 'Encaissée']['total_amount'].sum()

    print(f"Calculated from breakdown:")
    print(f"  Facturée: {facturee_amount:,.0f} €")
    print(f"  Encaissée: {encaissee_amount:,.0f} €")

except Exception as e:
    print(f"Error in breakdown: {e}")

print()
print("="*50)
print("CONCLUSION:")
print("="*50)
print("The corrected logic now:")
print("- Only counts 'Facture' documents (not 'Devis')")
print("- Separates 'Facturée' and 'Encaissée' status correctly")
print("- Follows the workflow: Posée → Confirmée → Facturée → Encaissée")