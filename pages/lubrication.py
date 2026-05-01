"""Page 06 - Module Lubrification"""

import dash
from dash import html, dcc, Input, Output, State, callback, dash_table

from components.cards import (
    page_header, section_title, footer, kpi_card,
    chart_card, recommendation_box, control_card,
)
from components.charts import lubricant_evolution, lubricants_comparison, COLORS
from components.icons import icon
from components.topbar import topbar
from core.cttd import (
    simuler_evolution_mu, predire_temps_remplacement, comparer_lubrifiants,
)
from core.parameters import load_lubricants_database


dash.register_page(__name__, path="/lubrication", name="Module Lubrification", order=6)

LUBRICANTS = load_lubricants_database()


layout = html.Div([
    topbar(["SAD LATRECA", "Modules", "Lubrification"]),

    page_header("drop", "Module Lubrification",
                "Vieillissement du lubrifiant et planification du remplacement",
                badge="MODULE · LIVE", pill="Suivi prédictif"),

    # Controls
    section_title("Conditions d'analyse"),
    control_card([
        html.Div(className="control-row", children=[
            html.Div([
                html.Label([
                    html.Span("Durée d'analyse"),
                    html.Span(id="duree-display",
                              className="control-value", children="365 jours"),
                ], style={"display": "flex", "justify-content": "space-between"}),
                dcc.Slider(id="lub-duree", min=30, max=730, value=365, step=30,
                            tooltip=None),
            ]),
            html.Div([
                html.Label([
                    html.Span("Température opérationnelle"),
                    html.Span(id="temp-display",
                              className="control-value", children="80°C"),
                ], style={"display": "flex", "justify-content": "space-between"}),
                dcc.Slider(id="lub-temp", min=25, max=140, value=80, step=5,
                            tooltip=None),
            ]),
        ]),
    ]),

    # KPIs
    html.Div(id="lub-kpis", className="kpi-grid"),

    # Chart evolution
    section_title("Évolution du lubrifiant actuel"),
    chart_card("Coefficient de frottement vs temps",
               dcc.Graph(id="lub-chart-evolution",
                         config={"displayModeBar": False})),

    # Comparaison
    section_title("Comparaison des lubrifiants disponibles", meta="04 lubrifiants"),
    chart_card("Évolution comparée",
               dcc.Graph(id="lub-chart-comparison",
                         config={"displayModeBar": False})),

    html.Div(id="lub-table"),

    html.Div(id="lub-recommendation"),

    footer(),
])


@callback(
    Output("duree-display", "children"),
    Input("lub-duree", "value"),
)
def upd_duree(v):
    return f"{int(v)} jours"


@callback(
    Output("temp-display", "children"),
    Input("lub-temp", "value"),
)
def upd_temp(v):
    return f"{int(v)}°C"


@callback(
    [Output("lub-kpis", "children"),
     Output("lub-chart-evolution", "figure"),
     Output("lub-chart-comparison", "figure"),
     Output("lub-table", "children"),
     Output("lub-recommendation", "children")],
    [Input("config-store", "data"),
     Input("lub-duree", "value"),
     Input("lub-temp", "value")],
)
def update_lub(store, duree, temp):
    if not store:
        store = {"mu_0": 0.060, "beta": 0.30, "gamma": 1.5e-6, "Q_lub": 65000.0}

    mu_0 = store.get("mu_0", 0.060)
    beta = store.get("beta", 0.30)
    gamma = store.get("gamma", 1.5e-6)
    Q_lub = store.get("Q_lub", 65000.0)

    # Evolution
    evolution = simuler_evolution_mu(
        mu_0=mu_0, beta=beta, gamma=gamma, Q_lub_J_mol=Q_lub,
        T_operation_C=temp, duree_simulation_jours=duree, n_points=200,
    )

    # Prediction
    prediction = predire_temps_remplacement(
        mu_0=mu_0, beta=beta, gamma=gamma, Q_lub_J_mol=Q_lub,
        T_operation_C=temp, facteur_critique=1.5,
    )

    # KPIs
    perf_finale = evolution['mu_array'][-1]
    degradation = (perf_finale / mu_0 - 1) * 100

    if prediction.get('avertissement'):
        kpi_remplacement = kpi_card(
            "check", "Statut lubrifiant", "Stable",
            trend="> 365j", trend_type="up",
            footer="Aucun remplacement requis",
            dark=True,
        )
    else:
        kpi_remplacement = kpi_card(
            "alert", "Remplacer dans",
            f"{prediction['t_remplacement_jours']:.0f}", unit=" j",
            trend=f"{prediction['t_remplacement_mois']:.1f} mois",
            trend_type="warning",
            footer="Prédiction CTTD",
            dark=True,
        )

    kpis = [
        kpi_card("drop", "Performance initiale",
                 f"{mu_0:.3f}",
                 trend="état neuf", trend_type="flat",
                 footer="Coefficient de frottement"),
        kpi_card("alert", "Seuil de remplacement",
                 f"{prediction['mu_cible']:.3f}",
                 trend="limite", trend_type="warning",
                 footer="μ critique = 1.5 × μ₀"),
        kpi_remplacement,
        kpi_card("trend-up", "Dégradation",
                 f"+{degradation:.0f}", unit="%",
                 trend=f"sur {duree}j", trend_type="warning",
                 footer="Augmentation prévue"),
    ]

    # Chart evolution dual-line + lignes verticales de reference
    age_actuel = store.get('age_lubrifiant_jours', 30)
    cycle_recommande = (
        prediction.get('t_remplacement_jours', None)
        if not prediction.get('avertissement') else None
    )
    fig_evo = lubricant_evolution(
        evolution['temps_jours'], evolution['mu_array'],
        evolution['mu_initial'], evolution['mu_critique'],
        nom="Lubrifiant actuel",
        age_actuel=age_actuel,
        cycle_recommande=cycle_recommande,
    )

    # Comparaison
    liste_lub = []
    for k, v in LUBRICANTS.items():
        if not k.startswith('_'):
            liste_lub.append({
                'nom': v['nom'], 'mu_0': v['mu_0'], 'beta': v['beta'],
                'gamma': v['gamma'], 'Q_lub': v['Q_lub'],
            })

    if liste_lub:
        comparaison = comparer_lubrifiants(
            liste_lubrifiants=liste_lub,
            T_operation_C=100.0, duree_jours=365,
        )
        fig_comp = lubricants_comparison(comparaison)

        table_data = []
        for r in comparaison:
            t_rempl = r['t_remplacement']['t_remplacement_jours']
            table_data.append({
                "Lubrifiant": r['nom'],
                "Performance initiale": f"{r['parametres']['mu_0']:.3f}",
                "Performance après 1 an": f"{r['evolution']['mu_array'][-1]:.3f}",
                "Durée de vie (jours)": (
                    f"{t_rempl:.0f}"
                    if not r['t_remplacement'].get('avertissement') else "> 365"
                ),
            })

        table = dash_table.DataTable(
            data=table_data,
            columns=[{"name": k, "id": k} for k in table_data[0].keys()],
            style_cell={"textAlign": "center", "fontFamily": "Inter",
                        "fontSize": "12.5px", "padding": "10px",
                        "border": "1px solid #E5DFCE"},
            style_header={"backgroundColor": "#0A2A1F", "color": "#F2D89A",
                          "fontFamily": "JetBrains Mono", "fontSize": "11px",
                          "fontWeight": "600", "textTransform": "uppercase",
                          "letterSpacing": "0.08em"},
            style_data_conditional=[{"if": {"row_index": "odd"},
                                     "backgroundColor": "#FAFAF7"}],
            style_table={"borderRadius": "14px", "overflow": "hidden",
                         "marginBottom": "16px"},
        )

        meilleur = max(comparaison,
                       key=lambda r: r['t_remplacement']['t_remplacement_jours'])
        rec = recommendation_box(
            f"Lubrifiant recommandé : {meilleur['nom']}",
            f"Durée de vie estimée : {meilleur['t_remplacement']['t_remplacement_jours']:.0f} "
            f"jours. Ce lubrifiant offre le meilleur compromis entre performance et longévité."
        )
    else:
        fig_comp = {}
        table = None
        rec = None

    return kpis, fig_evo, fig_comp, table, rec
