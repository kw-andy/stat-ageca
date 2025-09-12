import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from db import fetch_dataframe, month_expr

st.set_page_config(page_title="Dashboard Réservations & CA", layout="wide")

def build_combined_figure(df_resa, df_ca):
    """Build the combined dual-axis chart"""
    # Merge data
    resa = df_resa.copy() if not df_resa.empty else pd.DataFrame(columns=["mois", "nb_reservations"])
    ca = df_ca.copy() if not df_ca.empty else pd.DataFrame(columns=["mois", "ca_brut", "ca_net"])

    if not resa.empty:
        resa["mois"] = pd.to_datetime(resa["mois"])
    if not ca.empty:
        ca["mois"] = pd.to_datetime(ca["mois"])

    df = pd.merge(resa, ca, on="mois", how="outer").sort_values("mois")
    
    for col in ["nb_reservations", "ca_brut", "ca_net"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    fig = go.Figure()

    # Left axis - Reservations
    if "nb_reservations" in df.columns and not df.empty:
        fig.add_trace(
            go.Scatter(
                x=df["mois"],
                y=df["nb_reservations"],
                name="Réservations",
                mode="lines+markers",
                line=dict(width=3, color="red"),
                marker=dict(size=6),
                hovertemplate="%{x|%Y-%m}<br>Réservations: %{y}<extra></extra>",
                yaxis="y"
            )
        )

    # Right axis - CA brut
    if "ca_brut" in df.columns and not df.empty:
        fig.add_trace(
            go.Scatter(
                x=df["mois"],
                y=df["ca_brut"],
                name="CA brut (TTC)",
                mode="lines+markers",
                line=dict(width=3, color="blue"),
                marker=dict(size=6),
                hovertemplate="%{x|%Y-%m}<br>CA brut: %{y:,.0f} €<extra></extra>",
                yaxis="y2"
            )
        )

    # Right axis - CA net
    if "ca_net" in df.columns and not df.empty:
        fig.add_trace(
            go.Scatter(
                x=df["mois"],
                y=df["ca_net"],
                name="CA net (TTC)",
                mode="lines+markers",
                line=dict(width=3, color="green", dash="dash"),
                marker=dict(size=6),
                hovertemplate="%{x|%Y-%m}<br>CA net: %{y:,.0f} €<extra></extra>",
                yaxis="y2"
            )
        )

    fig.update_layout(
        title=dict(
            text="Réservations (axe gauche) vs CA brut & net (axe droit)",
            x=0.5,
            font=dict(size=20)
        ),
        hovermode="x unified",
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="center", 
            x=0.5
        ),
        height=600,
        xaxis=dict(
            title="Mois",
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray'
        ),
        yaxis=dict(
            title=dict(text="Nombre de réservations", font=dict(color="red")),
            rangemode="tozero",
            zeroline=True,
            tickfont=dict(color="red"),
            showgrid=True
        ),
        yaxis2=dict(
            title=dict(text="CA (€ TTC)", font=dict(color="blue")),
            overlaying="y",
            side="right",
            rangemode="tozero",
            zeroline=True,
            tickformat=",d",
            tickfont=dict(color="blue")
        ),
        plot_bgcolor='white'
    )
    
    return fig

def fetch_data(date_debut, date_fin, statut_sel, organisateur):
    """Fetch reservation and CA data"""
    
    # Build WHERE clauses
    wh, params = [], {}
    if date_debut:
        wh.append("doc_date >= :d1")
        params["d1"] = date_debut
    if date_fin:
        wh.append("doc_date < :d2")
        params["d2"] = date_fin
    if statut_sel:
        in_list = ",".join([f":s{i}" for i, _ in enumerate(statut_sel)])
        wh.append(f"status IN ({in_list})")
        for i, s in enumerate(statut_sel):
            params[f"s{i}"] = s
    if organisateur.strip():
        wh.append("organizer LIKE :org")
        params["org"] = f"%{organisateur.strip()}%"
    
    where_doc = " WHERE " + " AND ".join(wh) if wh else ""
    
    # Reservations query
    wh_r, params_r = [], {}
    if date_debut:
        wh_r.append("reservation_date >= :r1")
        params_r["r1"] = date_debut
    if date_fin:
        wh_r.append("reservation_date < :r2")
        params_r["r2"] = date_fin
    if organisateur.strip():
        wh_r.append("organizer LIKE :org")
        params_r["org"] = f"%{organisateur.strip()}%"
    
    where_resa = " WHERE " + " AND ".join(wh_r) if wh_r else ""
    
    # Execute queries
    try:
        m_resa = month_expr("reservation_date")
        sql_resa = f"""
            SELECT {m_resa} AS mois, COUNT(DISTINCT doc_number) AS nb_reservations
            FROM line_items
            {where_resa}
            GROUP BY 1
            ORDER BY 1
        """
        df_resa = fetch_dataframe(sql_resa, params_r)
        
        m_doc = month_expr("doc_date")
        sql_ca = f"""
            SELECT {m_doc} AS mois,
                   SUM(CASE WHEN NOT (doc_type LIKE 'Avoir%') THEN price_ttc*quantity ELSE 0 END) AS ca_brut,
                   SUM(CASE WHEN (doc_type LIKE 'Avoir%')
                            THEN -price_ttc*quantity ELSE price_ttc*quantity END) AS ca_net
            FROM line_items
            {where_doc}
            GROUP BY 1
            ORDER BY 1
        """
        df_ca = fetch_dataframe(sql_ca, params)
        
        return df_resa, df_ca, None
        
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), str(e)

# Streamlit UI
st.title("📊 Dashboard – Réservations & CA")

# Sidebar for filters
st.sidebar.header("🔍 Filtres")

col1, col2 = st.sidebar.columns(2)
with col1:
    date_debut = st.date_input("Date début", value=None)
with col2:
    date_fin = st.date_input("Date fin (exclue)", value=None)

statut_options = ["Encaissée", "Annulée", "Facturée", "Posée", "Confirmée"]
statut_sel = st.sidebar.multiselect(
    "Statut", 
    options=statut_options, 
    default=["Encaissée"]
)

organisateur = st.sidebar.text_input("Organisateur (contient)", "")

if st.sidebar.button("🔄 Actualiser"):
    st.rerun()

# Fetch data
with st.spinner("Chargement des données..."):
    df_resa, df_ca, error = fetch_data(date_debut, date_fin, statut_sel, organisateur)

if error:
    st.error(f"Erreur lors du chargement des données : {error}")
else:
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    total_reservations = df_resa["nb_reservations"].sum() if not df_resa.empty else 0
    total_ca_brut = df_ca["ca_brut"].sum() if not df_ca.empty else 0
    total_ca_net = df_ca["ca_net"].sum() if not df_ca.empty else 0
    
    with col1:
        st.metric("Total Réservations", f"{total_reservations:,}")
    with col2:
        st.metric("CA Brut Total", f"{total_ca_brut:,.0f} €")
    with col3:
        st.metric("CA Net Total", f"{total_ca_net:,.0f} €")
    
    # Create and display chart
    fig = build_combined_figure(df_resa, df_ca)
    st.plotly_chart(fig, use_container_width=True)
    
    # Display data tables
    if st.checkbox("Afficher les données détaillées"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Données Réservations")
            if not df_resa.empty:
                st.dataframe(df_resa, use_container_width=True)
            else:
                st.info("Aucune donnée de réservation")
        
        with col2:
            st.subheader("Données CA")
            if not df_ca.empty:
                # Format the CA data for display
                df_ca_display = df_ca.copy()
                for col in ["ca_brut", "ca_net"]:
                    if col in df_ca_display.columns:
                        df_ca_display[col] = df_ca_display[col].apply(lambda x: f"{x:,.0f} €")
                st.dataframe(df_ca_display, use_container_width=True)
            else:
                st.info("Aucune donnée de CA")