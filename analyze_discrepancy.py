#!/usr/bin/env python3
"""
Script to analyze discrepancies in September 2023 data
"""
import pandas as pd
from db import fetch_dataframe
from datetime import datetime

# Define September 2023 date range
date_debut = datetime(2023, 9, 1).date()
date_fin = datetime(2023, 10, 1).date()

print("=== DETAILED ANALYSIS OF SEPTEMBER 2023 DISCREPANCIES ===")
print()

# Let's break down by document type and status
sql_detailed = """
    SELECT
        doc_type,
        status,
        COUNT(*) as line_count,
        COUNT(DISTINCT doc_number) as doc_count,
        SUM(price_ttc * quantity) as total_amount,
        MIN(doc_date) as earliest_date,
        MAX(doc_date) as latest_date
    FROM line_items
    WHERE doc_date >= :d1 AND doc_date < :d2
    GROUP BY doc_type, status
    ORDER BY doc_type, status
"""

params = {"d1": date_debut, "d2": date_fin}

try:
    df_detailed = fetch_dataframe(sql_detailed, params)
    print("1. BREAKDOWN BY DOCUMENT TYPE AND STATUS:")
    print("="*50)
    for _, row in df_detailed.iterrows():
        print(f"{row['doc_type']:8s} | {row['status']:10s} | {row['doc_count']:3d} docs | {row['line_count']:4d} lines | {row['total_amount']:10,.0f} €")
    print()

    # Calculate totals like app.py does
    print("2. APP.PY CALCULATION LOGIC:")
    print("="*30)

    # CA Brut = sum of all non-Avoir documents
    ca_brut_items = df_detailed[~df_detailed['doc_type'].str.startswith('Avoir')]
    ca_brut = ca_brut_items['total_amount'].sum()
    print(f"CA Brut (Facturée) - All non-Avoir docs: {ca_brut:,.0f} €")

    # CA Net = CA Brut minus Avoir (credits)
    avoir_items = df_detailed[df_detailed['doc_type'].str.startswith('Avoir')]
    avoir_total = avoir_items['total_amount'].sum()
    ca_net = ca_brut - avoir_total
    print(f"Avoir (Credits) to subtract: {avoir_total:,.0f} €")
    print(f"CA Net (Encaissée) = CA Brut - Avoir: {ca_net:,.0f} €")
    print()

    # Let's check if there are specific status filters that should be applied
    print("3. STATUS ANALYSIS:")
    print("="*20)
    print("The app.py allows filtering by status, default is 'Encaissée'")
    print("Let's check what happens if we filter by status:")
    print()

    # Filter by Encaissée only (like the app default)
    encaissee_only = df_detailed[df_detailed['status'] == 'Encaissée']
    if not encaissee_only.empty:
        ca_brut_encaissee = encaissee_only[~encaissee_only['doc_type'].str.startswith('Avoir')]['total_amount'].sum()
        avoir_encaissee = encaissee_only[encaissee_only['doc_type'].str.startswith('Avoir')]['total_amount'].sum()
        ca_net_encaissee = ca_brut_encaissee - avoir_encaissee

        print(f"If we filter by 'Encaissée' status only:")
        print(f"  CA Brut: {ca_brut_encaissee:,.0f} €")
        print(f"  Avoir: {avoir_encaissee:,.0f} €")
        print(f"  CA Net: {ca_net_encaissee:,.0f} €")
        print()

    # Let's also check individual amounts to see if there are outliers
    print("4. INDIVIDUAL DOCUMENT ANALYSIS:")
    print("="*35)

    sql_docs = """
        SELECT
            doc_number,
            doc_type,
            status,
            doc_date,
            organizer,
            SUM(price_ttc * quantity) as doc_total
        FROM line_items
        WHERE doc_date >= :d1 AND doc_date < :d2
        GROUP BY doc_number, doc_type, status, doc_date, organizer
        ORDER BY doc_total DESC
        LIMIT 10
    """

    df_docs = fetch_dataframe(sql_docs, params)
    print("Top 10 highest value documents:")
    for _, row in df_docs.iterrows():
        print(f"{row['doc_number']:12s} | {row['doc_type']:8s} | {row['status']:10s} | {row['doc_total']:8,.0f} € | {row['organizer']}")
    print()

    # Check if there might be duplicate entries or wrong dates
    print("5. DATA QUALITY CHECKS:")
    print("="*25)

    sql_quality = """
        SELECT
            COUNT(*) as total_lines,
            COUNT(DISTINCT doc_number) as unique_docs,
            COUNT(DISTINCT CONCAT(doc_number, line_number)) as unique_line_items,
            MIN(doc_date) as earliest_date,
            MAX(doc_date) as latest_date,
            COUNT(DISTINCT organizer) as unique_organizers
        FROM line_items
        WHERE doc_date >= :d1 AND doc_date < :d2
    """

    df_quality = fetch_dataframe(sql_quality, params)
    quality = df_quality.iloc[0]
    print(f"Total line items: {quality['total_lines']}")
    print(f"Unique documents: {quality['unique_docs']}")
    print(f"Unique line items: {quality['unique_line_items']}")
    print(f"Date range: {quality['earliest_date']} to {quality['latest_date']}")
    print(f"Unique organizers: {quality['unique_organizers']}")
    print()

except Exception as e:
    print(f"Error in analysis: {e}")

print("=== SUMMARY ===")
print("The main discrepancy seems to be that the app is including ALL documents")
print("(Devis, Facture, Avoir) regardless of status, while your accounting")
print("may only be counting specific types or statuses.")
print()
print("Potential causes:")
print("1. App includes 'Devis' (quotes) which might not be in accounting")
print("2. App includes all statuses (Annulée, Posée, Encaissée)")
print("3. There might be different date criteria (doc_date vs other dates)")
print("4. Different treatment of 'Avoir' (credit notes)")