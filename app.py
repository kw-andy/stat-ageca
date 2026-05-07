import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, date
from db import fetch_dataframe, get_metadata, month_expr

# functions to :

# format

def format_number_fr(number):
    """Format number with French formatting (space as thousands separator)."""
    if pd.isna(number) or number == 0:
        return "0"
    num = int(round(number))
    formatted = "{:,}".format(abs(num)).replace(",", " ")
    return formatted if num >= 0 else "-" + formatted

def format_currency_fr(number):
    """Format currency with French formatting"""
    if pd.isna(number) or number == 0:
        return "0 €"
    
    return f"{format_number_fr(number)} €"

st.set_page_config(page_title="Dashboard Réservations & CA", layout="wide")

# build figures: build_combined_figure, build_gap_analysis_figure
# & build_correlation_figure

def build_combined_figure(df_resa, df_ca):
    """Build the combined dual-axis chart"""
    # Merge data
    resa = df_resa.copy() if not df_resa.empty else pd.DataFrame(columns=["mois", "nb_reservations"])
    ca = df_ca.copy() if not df_ca.empty else pd.DataFrame(columns=["mois", "ca_brut", "ca_net", "ecart"])

    if not resa.empty:
        resa["mois"] = pd.to_datetime(resa["mois"])
    if not ca.empty:
        ca["mois"] = pd.to_datetime(ca["mois"])

    df = pd.merge(resa, ca, on="mois", how="outer").sort_values("mois")
    
    for col in ["nb_reservations", "ca_brut", "ca_net"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Calculate normalized values (0-100%) for gap analysis
    if not df.empty and "nb_reservations" in df.columns and "ca_net" in df.columns:
        # Normalize both metrics to 0-100% scale for comparison
        resa_max = df["nb_reservations"].max() if df["nb_reservations"].max() > 0 else 1
        ca_max = df["ca_net"].max() if df["ca_net"].max() > 0 else 1
        
        df["resa_normalized"] = (df["nb_reservations"] / resa_max) * 100
        df["ca_normalized"] = (df["ca_net"] / ca_max) * 100
        df["gap_percentage"] = df["resa_normalized"] - df["ca_normalized"]

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
                name="CA Facturé (TTC)",
                mode="lines+markers",
                line=dict(width=3, color="blue"),
                marker=dict(size=6),
                hovertemplate="%{x|%Y-%m}<br>CA brut: %{y} €<extra></extra>",
                yaxis="y2"
            )
        )

    # Right axis - CA net
    if "ca_net" in df.columns and not df.empty:
        fig.add_trace(
            go.Scatter(
                x=df["mois"],
                y=df["ca_net"],
                name="CA Encaissé (TTC)",
                mode="lines+markers",
                line=dict(width=3, color="green", dash="dash"),
                marker=dict(size=6),
                hovertemplate="%{x|%Y-%m}<br>CA net: %{y} €<extra></extra>",
                yaxis="y2"
            )
        )

    # Ligne objectif mensuel
    if not df.empty:
        fig.add_shape(
            type="line",
            x0=df["mois"].min(), x1=df["mois"].max(),
            y0=40000, y1=40000,
            yref="y2",
            line=dict(color="orange", width=1.5, dash="dot"),
        )
        fig.add_annotation(
            x=df["mois"].max(), y=40000,
            yref="y2",
            text="Objectif 40 k€",
            showarrow=False,
            xanchor="right", yanchor="bottom",
            font=dict(color="orange", size=11),
        )

    fig.update_layout(
        title=dict(
            text="Réservations (axe gauche) vs CA Facturé & Encaissé (axe droit)",
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
            separatethousands=True,
            tickfont=dict(color="blue")
        ),
        plot_bgcolor='white'
    )
    
    return fig

def build_gap_analysis_figure(df_resa, df_ca):
    """Build gap analysis chart showing percentage difference"""
    # Merge data
    resa = df_resa.copy() if not df_resa.empty else pd.DataFrame(columns=["mois", "nb_reservations"])
    ca = df_ca.copy() if not df_ca.empty else pd.DataFrame(columns=["mois", "ca_brut", "ca_net", "ecart"])

    if not resa.empty:
        resa["mois"] = pd.to_datetime(resa["mois"])
    if not ca.empty:
        ca["mois"] = pd.to_datetime(ca["mois"])

    df = pd.merge(resa, ca, on="mois", how="outer").sort_values("mois")
    
    for col in ["nb_reservations", "ca_brut", "ca_net"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if df.empty:
        return go.Figure()

    # Calculate metrics
    # 1. CA per reservation
    df["ca_per_resa"] = np.where(
        df["nb_reservations"] > 0,
        df["ca_net"] / df["nb_reservations"],
        0
    )
    
    # 2. Normalized values (0-100%) for trend comparison
    resa_max = df["nb_reservations"].max() if df["nb_reservations"].max() > 0 else 1
    ca_max = df["ca_net"].max() if df["ca_net"].max() > 0 else 1
    
    df["resa_normalized"] = (df["nb_reservations"] / resa_max) * 100
    df["ca_normalized"] = (df["ca_net"] / ca_max) * 100
    df["gap_percentage"] = df["resa_normalized"] - df["ca_normalized"]

    fig = go.Figure()

    # Gap percentage (shows which metric is leading)
    fig.add_trace(
        go.Scatter(
            x=df["mois"],
            y=df["gap_percentage"],
            name="Écart de tendance (%)",
            mode="lines+markers",
            line=dict(width=3, color="purple"),
            marker=dict(size=6),
            hovertemplate="%{x|%Y-%m}<br>Écart: %{y:.1f}%<br>(>0: plus de résa, <0: plus de CA)<extra></extra>",
            fill='tonexty' if len(fig.data) > 0 else None
        )
    )

    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", 
                  annotation_text="Équilibre", annotation_position="top right")

    # CA per reservation (secondary axis)
    fig.add_trace(
        go.Scatter(
            x=df["mois"],
            y=df["ca_per_resa"],
            name="CA par réservation (€)",
            mode="lines+markers",
            line=dict(width=3, color="orange"),
            marker=dict(size=6),
            hovertemplate="%{x|%Y-%m}<br>CA/Résa: %{y} €<extra></extra>",
            yaxis="y2"
        )
    )

    fig.update_layout(
        title=dict(
            text="Analyse des écarts : Réservations vs CA",
            x=0.5,
            font=dict(size=18)
        ),
        hovermode="x unified",
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="center", 
            x=0.5
        ),
        height=500,
        xaxis=dict(
            title="Mois",
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray'
        ),
        yaxis=dict(
            title=dict(text="Écart de tendance (%)", font=dict(color="purple")),
            zeroline=True,
            tickfont=dict(color="purple"),
            showgrid=True
        ),
        yaxis2=dict(
            title=dict(text="CA par réservation (€)", font=dict(color="orange")),
            overlaying="y",
            side="right",
            rangemode="tozero",
            separatethousands=True,
            tickfont=dict(color="orange")
        ),
        plot_bgcolor='white'
    )
    
    return fig

def build_correlation_figure(df_resa, df_ca):
    """Build normalized comparison chart (both on 0-100% scale)"""
    # Merge data
    resa = df_resa.copy() if not df_resa.empty else pd.DataFrame(columns=["mois", "nb_reservations"])
    ca = df_ca.copy() if not df_ca.empty else pd.DataFrame(columns=["mois", "ca_brut", "ca_net", "ecart"])

    if not resa.empty:
        resa["mois"] = pd.to_datetime(resa["mois"])
    if not ca.empty:
        ca["mois"] = pd.to_datetime(ca["mois"])

    df = pd.merge(resa, ca, on="mois", how="outer").sort_values("mois")
    
    for col in ["nb_reservations", "ca_brut", "ca_net"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if df.empty:
        return go.Figure()

    # Normalize both to 0-100% scale
    resa_max = df["nb_reservations"].max() if df["nb_reservations"].max() > 0 else 1
    ca_max = df["ca_net"].max() if df["ca_net"].max() > 0 else 1
    
    df["resa_normalized"] = (df["nb_reservations"] / resa_max) * 100
    df["ca_normalized"] = (df["ca_net"] / ca_max) * 100

    fig = go.Figure()

    # Normalized reservations
    fig.add_trace(
        go.Scatter(
            x=df["mois"],
            y=df["resa_normalized"],
            name="Réservations (normalisé %)",
            mode="lines+markers",
            line=dict(width=3, color="red"),
            marker=dict(size=6),
            hovertemplate="%{x|%Y-%m}<br>Résa: %{y:.1f}%<extra></extra>"
        )
    )

    # Normalized CA
    fig.add_trace(
        go.Scatter(
            x=df["mois"],
            y=df["ca_normalized"],
            name="CA net (normalisé %)",
            mode="lines+markers",
            line=dict(width=3, color="green"),
            marker=dict(size=6),
            hovertemplate="%{x|%Y-%m}<br>CA: %{y:.1f}%<extra></extra>"
        )
    )

    fig.update_layout(
        title=dict(
            text="Tendances normalisées : Réservations vs CA (0-100%)",
            x=0.5,
            font=dict(size=18)
        ),
        hovermode="x unified",
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="center", 
            x=0.5
        ),
        height=500,
        xaxis=dict(
            title="Mois",
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray'
        ),
        yaxis=dict(
            title="Pourcentage du maximum (%)",
            range=[0, 105],
            showgrid=True,
            ticksuffix="%"
        ),
        plot_bgcolor='white'
    )
    
    return fig

# fetch data: calculate_gap_metrics & 
# fetch_data

def calculate_gap_metrics(df_resa, df_ca):
    """Calculate various gap metrics between reservations and CA"""
    if df_resa.empty or df_ca.empty:
        return {}
    
    # Merge data
    resa = df_resa.copy()
    ca = df_ca.copy()
    
    if not resa.empty:
        resa["mois"] = pd.to_datetime(resa["mois"])
    if not ca.empty:
        ca["mois"] = pd.to_datetime(ca["mois"])

    df = pd.merge(resa, ca, on="mois", how="outer").sort_values("mois")
    
    for col in ["nb_reservations", "ca_brut", "ca_net"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    
    if df.empty:
        return {}
    
    # Calculate various metrics
    metrics = {}
    
    # 1. Average CA per reservation
    total_resa = df["nb_reservations"].sum()
    total_ca = df["ca_net"].sum()
    metrics["ca_per_resa_avg"] = total_ca / total_resa if total_resa > 0 else 0
    
    # 2. Correlation coefficient
    if len(df) > 1:
        correlation = df["nb_reservations"].corr(df["ca_net"])
        metrics["correlation"] = correlation if not pd.isna(correlation) else 0
    else:
        metrics["correlation"] = 0
    
    # 3. Trend analysis (last 3 months vs previous period)
    if len(df) >= 6:
        recent_resa = df.tail(3)["nb_reservations"].mean()
        previous_resa = df.head(len(df)-3).tail(3)["nb_reservations"].mean()
        recent_ca = df.tail(3)["ca_net"].mean()
        previous_ca = df.head(len(df)-3).tail(3)["ca_net"].mean()
        
        if previous_resa > 0 and previous_ca > 0:
            resa_growth = ((recent_resa - previous_resa) / previous_resa) * 100
            ca_growth = ((recent_ca - previous_ca) / previous_ca) * 100
            metrics["resa_growth"] = resa_growth
            metrics["ca_growth"] = ca_growth
            metrics["growth_gap"] = resa_growth - ca_growth
    
    # 4. Efficiency metrics
    df["ca_per_resa"] = np.where(
        df["nb_reservations"] > 0,
        df["ca_net"] / df["nb_reservations"],
        0
    )
    metrics["ca_per_resa_trend"] = df["ca_per_resa"].pct_change().mean() * 100 if len(df) > 1 else 0
    
    return metrics

def fetch_data(date_debut, date_fin, statut_sel, organisateur):
    """Fetch reservation and CA data.

    Réservations et CA sont tous deux groupés par reservation_date
    (date d'utilisation de la salle), conformément à la logique validée
    le 2026-05-07. Le CA Brut inclut toutes les Factures et Avoirs quel
    que soit leur statut ; le CA Net se limite aux Factures Encaissées.
    """
    # Filtres communs (reservation_date + organisateur)
    wh, params = [], {}
    if date_debut:
        wh.append("reservation_date >= :r1")
        params["r1"] = date_debut
    if date_fin:
        wh.append("reservation_date < :r2")
        params["r2"] = date_fin
    if organisateur.strip():
        wh.append("organizer LIKE :org")
        params["org"] = f"%{organisateur.strip()}%"

    where = " WHERE " + " AND ".join(wh) if wh else ""

    try:
        m = month_expr("reservation_date")

        sql_resa = f"""
            SELECT {m} AS mois, COUNT(DISTINCT doc_number) AS nb_reservations
            FROM line_items
            {where}
            GROUP BY 1
            ORDER BY 1
        """
        df_resa = fetch_dataframe(sql_resa, params)

        sql_ca = f"""
            SELECT {m} AS mois,
                   SUM(CASE WHEN doc_type = 'Facture' THEN price_ttc*quantity ELSE 0 END) -
                   SUM(CASE WHEN doc_type = 'Avoir'   THEN price_ttc*quantity ELSE 0 END) AS ca_brut,
                   SUM(CASE WHEN doc_type = 'Facture' AND status = 'Encaissée'
                            THEN price_ttc*quantity ELSE 0 END)                            AS ca_net
            FROM line_items
            {where}
            GROUP BY 1
            ORDER BY 1
        """
        df_ca = fetch_dataframe(sql_ca, params)

        if not df_ca.empty:
            df_ca["ecart"] = df_ca["ca_brut"].fillna(0) - df_ca["ca_net"].fillna(0)
        else:
            df_ca = pd.DataFrame(columns=["mois", "ca_brut", "ca_net", "ecart"])

        return df_resa, df_ca, None

    except Exception as e:
        return (
            pd.DataFrame(columns=["mois", "nb_reservations"]),
            pd.DataFrame(columns=["mois", "ca_brut", "ca_net", "ecart"]),
            str(e),
        )

# Display des graphiques

# Streamlit UI
st.title("📊 Dashboard – Réservations & CA")

# Sidebar for filters
st.sidebar.header("🔍 Filtres")

_today = date.today()
_debut_defaut = date(_today.year, 1, 1)

col1, col2 = st.sidebar.columns(2)
with col1:
    date_debut = st.date_input("Date début", value=_debut_defaut)
with col2:
    date_fin = st.date_input("Date fin (exclue)", value=_today)

statut_options = ["Posée", "Confirmée", "Facturée", "Encaissée", "Annulée"]
statut_sel = st.sidebar.multiselect(
    "Statut",
    options=statut_options,
    default=["Facturée", "Encaissée"]
)

organisateur = st.sidebar.text_input("Organisateur (contient)", "")

# Chart selection
chart_type = st.sidebar.selectbox(
    "Type d'analyse",
    ["Vue d'ensemble", "Analyse des écarts", "Tendances normalisées"]
)

if st.sidebar.button("🔄 Actualiser"):
    st.rerun()

# Métadonnées — timestamp logique comptable
meta = get_metadata()
if meta:
    st.sidebar.markdown("---")
    st.sidebar.caption("**Données**")
    src = meta.get("data_source", {}).get("value", "—")
    imported = meta.get("data_imported_at", {}).get("value", "—")
    validated = meta.get("logic_validated_at", {}).get("value", "—")
    st.sidebar.caption(f"Source : {src}")
    st.sidebar.caption(f"Importé le : {imported}")
    st.sidebar.caption(f"Logique validée le : {validated}")

# Fetch data
with st.spinner("Chargement des données..."):
    df_resa, df_ca, error = fetch_data(date_debut, date_fin, statut_sel, organisateur)

if error:
    st.error(f"Erreur lors du chargement des données : {error}")
else:
    # Calculate gap metrics
    gap_metrics = calculate_gap_metrics(df_resa, df_ca)
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_reservations = df_resa["nb_reservations"].sum() if not df_resa.empty else 0
    total_ca_brut = df_ca["ca_brut"].sum() if not df_ca.empty else 0
    total_ca_net = df_ca["ca_net"].sum() if not df_ca.empty else 0
    
    with col1:
        st.metric("Total Réservations", format_number_fr(total_reservations))
    with col2:
        st.metric("CA Brut Total", format_currency_fr(total_ca_brut))
    with col3:
        st.metric("CA Net Total", format_currency_fr(total_ca_net))
    with col4:
        ca_per_resa = gap_metrics.get("ca_per_resa_avg", 0)
        st.metric("CA moyen / Résa", format_currency_fr(ca_per_resa))
    
    # Gap analysis metrics
    if gap_metrics:
        st.subheader("📈 Analyse des écarts")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            correlation = gap_metrics.get("correlation", 0)
            correlation_text = "Forte" if abs(correlation) > 0.7 else "Modérée" if abs(correlation) > 0.3 else "Faible"
            st.metric(
                "Corrélation Résa ↔ CA", 
                f"{correlation:.2f}",
                help=f"Corrélation {correlation_text} ({'positive' if correlation > 0 else 'négative'})"
            )
        
        with col2:
            if "growth_gap" in gap_metrics:
                growth_gap = gap_metrics["growth_gap"]
                st.metric(
                    "Écart de croissance", 
                    f"{growth_gap:+.1f}%",
                    help="Différence entre la croissance des réservations et du CA"
                )
        
        with col3:
            if "ca_per_resa_trend" in gap_metrics:
                efficiency_trend = gap_metrics["ca_per_resa_trend"]
                st.metric(
                    "Évolution efficacité", 
                    f"{efficiency_trend:+.1f}%",
                    help="Évolution du CA par réservation"
                )
    
    # Display appropriate chart based on selection
    if chart_type == "Vue d'ensemble":
        fig = build_combined_figure(df_resa, df_ca)
        st.plotly_chart(fig, use_container_width=True)
        
    elif chart_type == "Analyse des écarts":
        fig = build_gap_analysis_figure(df_resa, df_ca)
        st.plotly_chart(fig, use_container_width=True)
        
        # Add interpretation
        st.info("""
        **Comment lire ce graphique :**
        - **Écart de tendance** (violet) : >0 = plus de réservations relatives, <0 = plus de CA relatif
        - **CA par réservation** (orange) : efficacité commerciale par réservation
        - La ligne grise indique l'équilibre parfait entre les tendances
        """)
        
    elif chart_type == "Tendances normalisées":
        fig = build_correlation_figure(df_resa, df_ca)
        st.plotly_chart(fig, use_container_width=True)
        
        st.info("""
        **Comment lire ce graphique :**
        - Les deux métriques sont normalisées sur la même échelle 0-100%
        - Permet de comparer directement les tendances
        - Les courbes parallèles indiquent une bonne corrélation
        """)
    
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
                for col in ["ca_brut", "ca_net", "ecart"]:
                    if col in df_ca_display.columns:
                        df_ca_display[col] = df_ca_display[col].apply(lambda x: format_currency_fr(x))
                st.dataframe(df_ca_display, use_container_width=True)
            else:
                st.info("Aucune donnée de CA")
    
    # Advanced analytics section
    if st.checkbox("🔬 Analyses avancées"):
        if not df_resa.empty and not df_ca.empty:
            # Merge data for detailed analysis
            resa = df_resa.copy()
            ca = df_ca.copy()
            
            if not resa.empty:
                resa["mois"] = pd.to_datetime(resa["mois"])
            if not ca.empty:
                ca["mois"] = pd.to_datetime(ca["mois"])

            df_merged = pd.merge(resa, ca, on="mois", how="outer").sort_values("mois")
            
            for col in ["nb_reservations", "ca_brut", "ca_net"]:
                if col in df_merged.columns:
                    df_merged[col] = pd.to_numeric(df_merged[col], errors="coerce").fillna(0)
            
            # Calculate additional metrics
            df_merged["ca_per_resa"] = df_merged["ca_net"] / df_merged["nb_reservations"].replace(0, 1)
            df_merged["ecart_brut_net"] = df_merged["ca_brut"] - df_merged["ca_net"]
            df_merged["taux_annulation"] = (df_merged["ecart_brut_net"] / df_merged["ca_brut"].replace(0, 1)) * 100
            
            # Display advanced metrics table
            st.subheader("Tableau d'analyse détaillée")
            
            # Format for display
            df_display = df_merged.copy()
            df_display["mois"] = df_display["mois"].dt.strftime("%Y-%m")
            df_display["ca_per_resa"] = df_display["ca_per_resa"].apply(lambda x: format_number_fr(x))
            df_display["taux_annulation"] = df_display["taux_annulation"].round(1)
            df_display["ca_brut"] = df_display["ca_brut"].apply(lambda x: format_number_fr(x))
            df_display["ca_net"] = df_display["ca_net"].apply(lambda x: format_number_fr(x))
            
            # Select and rename columns for display
            columns_to_show = {
                "mois": "Mois",
                "nb_reservations": "Réservations",
                "ca_brut": "CA Brut (€)",
                "ca_net": "CA Net (€)",
                "ca_per_resa": "CA/Résa (€)",
                "taux_annulation": "Taux annulation (%)"
            }
            
            df_final = df_display[list(columns_to_show.keys())].rename(columns=columns_to_show)
            st.dataframe(df_final, use_container_width=True)
            
            # Summary insights
            st.subheader("🔍 Insights automatiques")
            
            insights = []
            
            # Best and worst months
            # BEFORE: Fixed idxmax() KeyError when all values are zero
            if len(df_merged) > 0:
                best_resa_month = None
                best_ca_month = None

                if df_merged["nb_reservations"].max() > 0:  # Has actual reservations
                    best_resa_month = pd.to_datetime(df_merged.loc[df_merged["nb_reservations"].idxmax(), "mois"]).strftime("%Y-%m")
                    insights.append(f"📅 **Meilleur mois réservations** : {best_resa_month}")

                if df_merged["ca_net"].max() > 0:  # Has actual revenue
                    best_ca_month = pd.to_datetime(df_merged.loc[df_merged["ca_net"].idxmax(), "mois"]).strftime("%Y-%m")
                    insights.append(f"💰 **Meilleur mois CA** : {best_ca_month}")

                if best_resa_month and best_ca_month and best_resa_month != best_ca_month:
                    insights.append("⚠️ Les pics de réservations et de CA ne coïncident pas")
            # AFTER: idxmax() now safely handles zero-only columns
                
                # Efficiency analysis
                avg_ca_per_resa = df_merged["ca_per_resa"].mean()
                insights.append(f"🎯 **CA moyen par réservation** : {format_currency_fr(avg_ca_per_resa)}")

                if df_merged["ca_per_resa"].max() > 0:  # Has actual efficiency data
                    best_efficiency_month = pd.to_datetime(df_merged.loc[df_merged["ca_per_resa"].idxmax(), "mois"]).strftime("%Y-%m")
                    insights.append(f"🏆 **Mois le plus efficace** : {best_efficiency_month}")
                
                # Trend analysis
                if len(df_merged) >= 3:
                    recent_efficiency = df_merged.tail(3)["ca_per_resa"].mean()
                    if recent_efficiency > avg_ca_per_resa * 1.1:
                        insights.append("📈 L'efficacité commerciale s'améliore récemment")
                    elif recent_efficiency < avg_ca_per_resa * 0.9:
                        insights.append("📉 L'efficacité commerciale décline récemment")
            
            for insight in insights:
                st.write(insight)
        else:
            st.info("Analyses avancées disponibles quand les données de réservations et CA sont présentes.")