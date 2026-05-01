"""Page 03 - Module Materiau"""

import dash
from dash import html, dcc, Input, Output, callback, dash_table

from components.cards import (
    page_header, section_title, footer, kpi_card,
    chart_card, recommendation_box,
)
from components.charts import hollomon_curve, resistance_per_stage, COLORS
from components.topbar import topbar
from core.hollomon import calculer_profil_contraintes


dash.register_page(__name__, path="/material", name="Module Matériau", order=3)


layout = html.Div([
    topbar(["SAD LATRECA", "Modules", "Matériau"]),

    page_header("layers", "Module Matériau",
                "Comportement et résistance du fil le long de la ligne · Loi de Hollomon",
                badge="MODULE · LIVE", pill="Cuivre ETP"),

    # KPIs
    html.Div(id="material-kpis", className="kpi-grid"),

    # Charts en grille 2x1
    section_title("Visualisations", meta="02 graphiques"),
    html.Div(className="chart-grid-2", children=[
        chart_card("Comportement du matériau",
                   dcc.Graph(id="material-chart-curve",
                             config={"displayModeBar": False})),
        chart_card("Résistance par étape",
                   dcc.Graph(id="material-chart-bars",
                             config={"displayModeBar": False})),
    ]),

    # Tableau
    section_title("Évolution étape par étape"),
    html.Div(id="material-table"),

    # Recommandation
    html.Div(id="material-recommendation"),

    footer(),
])


# ════ Callbacks ════
@callback(
    [Output("material-kpis", "children"),
     Output("material-chart-curve", "figure"),
     Output("material-chart-bars", "figure"),
     Output("material-table", "children"),
     Output("material-recommendation", "children")],
    Input("config-store", "data"),
)
def update_material(store):
    if not store:
        store = {"K": 335, "n": 0.5, "d_0": 8.0, "d_f": 2.0, "n_passes": 9}

    K = store.get("K", 335.0)
    n = store.get("n", 0.50)
    d_0 = store.get("d_0", 8.0)
    d_f = store.get("d_f", 2.0)
    n_passes = int(store.get("n_passes", 9))

    profil = calculer_profil_contraintes(d_0, d_f, n_passes, K, n)
    sigma_finale = profil['contraintes_par_passe'][-1]
    eps_finale = profil['deformations_cumulees'][-1]
    durcissement = sigma_finale / max(profil['contraintes_par_passe'][1], 1)
    reduction = (1 - (d_f / d_0) ** 2) * 100

    # KPIs
    kpis = [
        kpi_card("zap", "Résistance finale",
                 f"{sigma_finale:.0f}", unit=" MPa",
                 trend="optimal", trend_type="up",
                 footer=f"Durcissement ×{durcissement:.1f}"),
        kpi_card("chart", "Déformation totale",
                 f"{eps_finale:.2f}",
                 trend="cumulée", trend_type="flat",
                 footer=f"Sur {n_passes} étapes",
                 dark=True),
        kpi_card("activity", "Facteur durcissement",
                 f"×{durcissement:.1f}",
                 trend="multiplication", trend_type="up",
                 footer="Résistance multipliée"),
        kpi_card("package", "Réduction section",
                 f"{reduction:.0f}", unit="%",
                 trend="globale", trend_type="up",
                 footer=f"De Ø{d_0:.1f} → Ø{d_f:.1f} mm"),
    ]

    # Graphiques
    fig_curve = hollomon_curve(K=K, n=n, current_eps=eps_finale)
    fig_bars = resistance_per_stage(profil)

    # Tableau
    table_data = []
    sigmas_moy = ["—"] + [f"{s:.1f}" for s in profil['contraintes_moyennes']]
    for i in range(n_passes + 1):
        table_data.append({
            "Étape": i,
            "Diamètre (mm)": f"{profil['diametres'][i]:.2f}",
            "Déformation": f"{profil['deformations_cumulees'][i]:.3f}",
            "Résistance (MPa)": f"{profil['contraintes_par_passe'][i]:.1f}",
            "Résistance moy. (MPa)": sigmas_moy[i],
        })

    table = dash_table.DataTable(
        data=table_data,
        columns=[{"name": k, "id": k} for k in table_data[0].keys()],
        style_cell={
            "textAlign": "center",
            "fontFamily": "Inter",
            "fontSize": "13px",
            "padding": "10px",
            "border": "1px solid #E5DFCE",
        },
        style_header={
            "backgroundColor": "#0A2A1F",
            "color": "#F2D89A",
            "fontFamily": "JetBrains Mono",
            "fontSize": "11px",
            "fontWeight": "600",
            "textTransform": "uppercase",
            "letterSpacing": "0.08em",
            "border": "1px solid #0A2A1F",
        },
        style_data_conditional=[
            {"if": {"row_index": "odd"},
             "backgroundColor": "#FAFAF7"},
        ],
        style_table={"borderRadius": "14px", "overflow": "hidden",
                     "border": "1px solid #E5DFCE"},
    )

    # Recommandation
    rec = recommendation_box(
        "Recommandation",
        f"La résistance finale du matériau est de {sigma_finale:.0f} MPa avec un "
        f"facteur de durcissement de ×{durcissement:.1f}. Vérifiez que les efforts "
        f"de production restent dans la zone de sécurité (Module Forces).",
    )

    return kpis, fig_curve, fig_bars, table, rec
