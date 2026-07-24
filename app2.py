import streamlit as st
import pandas as pd
import plotly.express as px

# ===========================================================
# 1. CONFIGURATION DE LA PAGE
# ===========================================================

st.set_page_config(
    page_title="Maroc - Emploi, Population & PIB",
    page_icon="data/197551.png",
    layout="wide",
)

# Palette de couleurs cohérente, réutilisée dans tous les graphiques Plotly
PALETTE = px.colors.qualitative.Set2

# ===========================================================
# 2. CHARGEMENT ET NETTOYAGE DES DONNÉES
# ===========================================================

@st.cache_data
def load_wide_csv(path, value_name):
    """Lit un CSV au format large (une colonne par année) et le transforme en format long."""
    df = pd.read_csv(path)
    geo_col = df.columns[0]
    df[geo_col] = df[geo_col].str.strip()

    year_cols = [c for c in df.columns if c.strip().isdigit()]

    df_long = pd.melt(
        df,
        id_vars=[geo_col],
        value_vars=year_cols,
        var_name="Annee",
        value_name=value_name,
    )
    df_long["Annee"] = df_long["Annee"].astype(int)
    df_long = df_long.rename(columns={geo_col: "Zone"})
    df_long = df_long.dropna(subset=[value_name])
    return df_long


@st.cache_data
def load_activite(path):
    """Lit le fichier taux d'activité 2024 (National > Région > Provinces via indentation)."""
    df = pd.read_csv(path)
    geo_col = df.columns[0]
    value_col = df.columns[-1]

    df["niveau_indent"] = df[geo_col].apply(lambda x: len(x) - len(x.lstrip(" ")))
    df[geo_col] = df[geo_col].str.strip()
    df = df.rename(columns={geo_col: "Zone", value_col: "Taux_activite"})

    niveaux_tries = sorted(df["niveau_indent"].unique())
    labels = ["National", "Region", "Province"]
    niveau_map = {
        niveau: (labels[i] if i < len(labels) else "Province")
        for i, niveau in enumerate(niveaux_tries)
    }
    df["Niveau"] = df["niveau_indent"].map(niveau_map)
    return df[["Zone", "Niveau", "Taux_activite"]]


df_chomage = load_wide_csv("data/indicateur_TC.csv", "Taux_chomage")
df_population = load_wide_csv("data/indicateur_population.csv", "Population")
df_activite = load_activite("data/indicateur_I154.csv")
df_pib = load_wide_csv("data/indicateur_ContributionPIB.csv", "Contribution_PIB")  # NOUVEAU

regions = sorted([z for z in df_chomage["Zone"].unique() if z != "National"])

# ===========================================================
# 3. SIDEBAR : NAVIGATION + FILTRES
# ===========================================================

st.sidebar.title("HCP Dashboard")
st.sidebar.caption("Emploi · Population · PIB — par région")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Accueil",
        "📈 Évolution",
        "📊 Comparaison régions",
        "💰 Contribution au PIB",
        "🔎 Focus Souss-Massa",
    ],
    captions=[
        "Vue d'ensemble et KPIs",
        "Tendances 2015-2024",
        "Classement régional",
        "Part de chaque région",
        "Provinces de Souss-Massa",
    ],
)
st.sidebar.divider()

# ===========================================================
# 4. PAGE : ACCUEIL
# ===========================================================

if page == "🏠 Accueil":
    st.title("Emploi, Population & PIB par région")
    st.caption("Tableau de bord des indicateurs socio-économiques régionaux")

    derniere_annee = df_chomage["Annee"].max()
    annee_precedente = derniere_annee - 1

    chomage_national = df_chomage[
        (df_chomage["Zone"] == "National") & (df_chomage["Annee"] == derniere_annee)
    ]["Taux_chomage"].values[0]
    chomage_national_prec = df_chomage[
        (df_chomage["Zone"] == "National") & (df_chomage["Annee"] == annee_precedente)
    ]["Taux_chomage"].values[0]

    pop_national = df_population[
        (df_population["Zone"] == "National") & (df_population["Annee"] == derniere_annee)
    ]["Population"].values[0]

    derniere_annee_pib = df_pib["Annee"].max()
    pib_souss_massa = df_pib[
        (df_pib["Zone"] == "Souss-Massa") & (df_pib["Annee"] == derniere_annee_pib)
    ]["Contribution_PIB"].values[0]

    chomage_derniere_annee = df_chomage[
        (df_chomage["Zone"] != "National") & (df_chomage["Annee"] == derniere_annee)
    ]
    region_max = chomage_derniere_annee.loc[chomage_derniere_annee["Taux_chomage"].idxmax()]
    region_min = chomage_derniere_annee.loc[chomage_derniere_annee["Taux_chomage"].idxmin()]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        f"Taux de chômage national ({derniere_annee})",
        f"{chomage_national} %",
        f"{round(chomage_national - chomage_national_prec, 1)} pts vs {annee_precedente}",
        delta_color="inverse",
    )
    col2.metric(f"Population nationale ({derniere_annee})", f"{int(pop_national):,}".replace(",", " "))
    col3.metric(f"Contribution PIB Souss-Massa ({derniere_annee_pib})", f"{pib_souss_massa} %")
    col4.metric("Région chômage le + élevé", region_max["Zone"], f"{region_max['Taux_chomage']} %")

    st.markdown("")
    st.info(
        "Utilise le menu à gauche pour explorer l'évolution temporelle, "
        "comparer les régions, ou zoomer sur la contribution au PIB et sur Souss-Massa."
    )

# ===========================================================
# 5. PAGE : ÉVOLUTION
# ===========================================================

elif page == "📈 Évolution":
    st.title("Évolution 2015-2024")
    st.caption("Suivi temporel des indicateurs par région")

    indicateur = st.sidebar.selectbox("Indicateur", ["Taux de chômage", "Population"])
    zones_choisies = st.sidebar.multiselect(
        "Régions à afficher", ["National"] + regions, default=["National", "Souss-Massa"]
    )

    if indicateur == "Taux de chômage":
        df_plot = df_chomage[df_chomage["Zone"].isin(zones_choisies)].copy()
        y_col, titre = "Taux_chomage", "Évolution du taux de chômage (%)"
    else:
        df_plot = df_population[
            (df_population["Zone"].isin(zones_choisies)) & (df_population["Annee"] <= 2024)
        ].copy()
        y_col, titre = "Population", "Évolution de la population"

    df_plot["Annee"] = df_plot["Annee"].astype(str)
    fig = px.line(
        df_plot, x="Annee", y=y_col, color="Zone", markers=True, title=titre,
        color_discrete_sequence=PALETTE,
    )
    fig.update_xaxes(type="category")
    fig.update_layout(template="plotly_white", title_font_size=18)
    st.plotly_chart(fig, use_container_width=True)

# ===========================================================
# 6. PAGE : COMPARAISON RÉGIONS
# ===========================================================

elif page == "📊 Comparaison régions":
    st.title("Comparaison des régions")
    st.caption("Classement régional pour une année donnée")

    indicateur = st.sidebar.selectbox("Indicateur", ["Taux de chômage", "Population"])
    annee = st.sidebar.slider("Année", 2015, 2024, 2024)

    if indicateur == "Taux de chômage":
        df_plot = df_chomage[(df_chomage["Zone"] != "National") & (df_chomage["Annee"] == annee)]
        df_plot = df_plot.sort_values("Taux_chomage", ascending=True)
        fig = px.bar(
            df_plot, x="Taux_chomage", y="Zone", orientation="h",
            title=f"Taux de chômage par région ({annee})",
            color="Taux_chomage", color_continuous_scale="Blues",
        )
    else:
        df_plot = df_population[(df_population["Zone"] != "National") & (df_population["Annee"] == annee)]
        df_plot = df_plot.sort_values("Population", ascending=True)
        fig = px.bar(
            df_plot, x="Population", y="Zone", orientation="h",
            title=f"Population par région ({annee})",
            color="Population", color_continuous_scale="Blues",
        )

    fig.update_layout(template="plotly_white", title_font_size=18)
    st.plotly_chart(fig, use_container_width=True)

# ===========================================================
# 7. PAGE : CONTRIBUTION AU PIB (NOUVELLE PAGE)
# ===========================================================

elif page == "💰 Contribution au PIB":
    st.title("Contribution des régions au PIB national")
    st.caption("Part de chaque région dans le PIB national, en % (2015-2023)")

    annee_pib = st.sidebar.slider(
        "Année", int(df_pib["Annee"].min()), int(df_pib["Annee"].max()), int(df_pib["Annee"].max())
    )
    type_graphique = st.sidebar.selectbox("Type de graphique", ["Bar", "Pie", "Line"])

    df_regions_pib = df_pib[df_pib["Zone"] != "National"].copy()

    if type_graphique == "Bar":
        df_plot = df_regions_pib[df_regions_pib["Annee"] == annee_pib].sort_values(
            "Contribution_PIB", ascending=True
        )
        fig = px.bar(
            df_plot, x="Contribution_PIB", y="Zone", orientation="h",
            title=f"Contribution au PIB par région ({annee_pib})",
            color="Zone", color_discrete_sequence=PALETTE,
            text="Contribution_PIB",
        )
        fig.update_traces(texttemplate="%{text} %", textposition="outside")
        fig.update_layout(showlegend=False)

    elif type_graphique == "Pie":
        df_plot = df_regions_pib[df_regions_pib["Annee"] == annee_pib]
        fig = px.pie(
            df_plot, names="Zone", values="Contribution_PIB",
            title=f"Répartition du PIB par région ({annee_pib})",
            color_discrete_sequence=PALETTE,
            hole=0.35,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")

    else:  # Line
        zones_pib = st.sidebar.multiselect(
            "Régions à comparer", regions, default=["Souss-Massa", "Casablanca-Settat"]
        )
        df_plot = df_regions_pib[df_regions_pib["Zone"].isin(zones_pib)].copy()
        df_plot["Annee"] = df_plot["Annee"].astype(str)
        fig = px.line(
            df_plot, x="Annee", y="Contribution_PIB", color="Zone", markers=True,
            title="Évolution de la contribution au PIB (%)",
            color_discrete_sequence=PALETTE,
        )
        fig.update_xaxes(type="category")

    fig.update_layout(template="plotly_white", title_font_size=18)
    st.plotly_chart(fig, use_container_width=True)

# ===========================================================
# 8. PAGE : FOCUS SOUSS-MASSA
# ===========================================================

elif page == "🔎 Focus Souss-Massa":
    st.title("Focus Souss-Massa")
    st.caption("Taux d'activité par province (2024)")

    df_provinces = df_activite[df_activite["Niveau"] == "Province"]
    valeur_nationale = df_activite[df_activite["Niveau"] == "National"]["Taux_activite"].values[0]
    valeur_regionale = df_activite[df_activite["Niveau"] == "Region"]["Taux_activite"].values[0]

    fig = px.bar(
        df_provinces.sort_values("Taux_activite"), x="Taux_activite", y="Zone",
        orientation="h", title="Taux d'activité par province (Souss-Massa, 2024)",
        color="Taux_activite", color_continuous_scale="Teal",
    )
    fig.add_vline(
        x=valeur_nationale, line_dash="dash", line_color="red",
        annotation_text=f"National ({valeur_nationale}%)", annotation_position="top right",
    )
    fig.add_vline(
        x=valeur_regionale, line_dash="dash", line_color="green",
        annotation_text=f"Région ({valeur_regionale}%)", annotation_position="bottom right",
    )
    fig.update_layout(template="plotly_white", title_font_size=18)
    st.plotly_chart(fig, use_container_width=True)