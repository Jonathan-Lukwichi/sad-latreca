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
                              className="control-value",
                              children="60 jours"),
                ], style={"display": "flex",
                          "justify-content": "space-between"}),
                dcc.Slider(id="lub-duree", min=30, max=365, value=60,
                           step=15, tooltip=None),
            ]),
            html.Div([
                html.Label([
                    html.Span("Température opérationnelle"),
                    html.Span(id="temp-display",
                              className="control-value", children="80°C"),
                ], style={"display": "flex",
                          "justify-content": "space-between"}),
                dcc.Slider(id="lub-temp", min=25, max=140, value=80,
                           step=5, tooltip=None),
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

    # ─── KPIs : version maquette Streamlit ───
    age_actuel = int(store.get('age_lubrifiant_jours', 30))
    cycle_recommande_jours = (
        int(prediction['t_remplacement_jours'])
        if not prediction.get('avertissement')
        else 365
    )

    # Etat courant : interpoler mu(t = age_actuel) sur la courbe
    import numpy as _np
    t_arr = _np.array(evolution['temps_jours'])
    mu_arr = _np.array(evolution['mu_array'])
    if age_actuel <= t_arr[-1]:
        mu_actuel = float(_np.interp(age_actuel, t_arr, mu_arr))
    else:
        mu_actuel = float(mu_arr[-1])

    # Viscosite residuelle (% du neuf) : decroit en miroir de mu
    visc_pct = (100.0 * mu_0 / mu_actuel) if mu_actuel > 0 else 100.0
    visc_pct = max(25.0, min(100.0, visc_pct))

    # KPI 1 : Age du lubrifiant (jour X / cycle Y)
    age_trend_type = ("warning" if age_actuel > cycle_recommande_jours * 0.7
                       else "up")
    delta_jours = age_actuel - cycle_recommande_jours
    if delta_jours > 0:
        age_pill = f"+{delta_jours}j vs cycle"
        age_trend_type = "down"
    elif age_actuel > cycle_recommande_jours * 0.7:
        age_pill = f"reste {cycle_recommande_jours - age_actuel}j"
    else:
        age_pill = f"jeune ({age_actuel}/{cycle_recommande_jours}j)"

    # KPI 2 : Viscosite residuelle (% du neuf, seuil 70%)
    visc_trend_type = ("up" if visc_pct >= 80 else
                        "warning" if visc_pct >= 70 else "down")

    # KPI 3 : Coefficient de frottement actuel μ
    mu_increase_pct = ((mu_actuel - mu_0) / mu_0 * 100) if mu_0 > 0 else 0
    mu_trend_type = ("up" if mu_increase_pct < 30 else
                      "warning" if mu_increase_pct < 60 else "down")

    # KPI 4 : Prochain remplacement
    if prediction.get('avertissement'):
        rempl_value = "Stable"
        rempl_trend = "> 365j"
        rempl_type = "up"
        rempl_footer = "aucun remplacement requis"
    else:
        jours_restants = max(0,
                              int(prediction['t_remplacement_jours'])
                              - age_actuel)
        if jours_restants <= 0:
            rempl_value = "Aujourd'hui"
            rempl_trend = "J-0"
            rempl_type = "down"
            rempl_footer = "action immédiate recommandée"
        elif jours_restants < 7:
            rempl_value = f"Dans {jours_restants}j"
            rempl_trend = f"J-{jours_restants}"
            rempl_type = "warning"
            rempl_footer = "à planifier cette semaine"
        else:
            rempl_value = f"Dans {jours_restants}j"
            rempl_trend = f"J-{jours_restants}"
            rempl_type = "up"
            rempl_footer = "prédiction CTTD μ(T,t)"

    kpis = [
        kpi_card("drop", "Âge lubrifiant",
                 f"{age_actuel}", unit=" j",
                 trend=age_pill, trend_type=age_trend_type,
                 footer=f"cycle recommandé : {cycle_recommande_jours} j"),
        kpi_card("activity", "Viscosité résiduelle",
                 f"{visc_pct:.0f}", unit=" %",
                 trend=f"{visc_pct - 100:+.0f}% vs neuf",
                 trend_type=visc_trend_type,
                 footer="seuil minimum 70 %",
                 dark=True),
        kpi_card("alert", "Coefficient frottement μ",
                 f"{mu_actuel:.3f}",
                 trend=f"{mu_increase_pct:+.0f}% vs μ₀",
                 trend_type=mu_trend_type,
                 footer=f"nominal μ₀ = {mu_0:.3f}"),
        kpi_card("calendar", "Prochain remplacement",
                 rempl_value,
                 trend=rempl_trend, trend_type=rempl_type,
                 footer=rempl_footer),
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
