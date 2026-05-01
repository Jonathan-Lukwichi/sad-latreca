"""Page 07 - Module Optimisation"""

import dash
from dash import html, dcc, Input, Output, State, callback, dash_table, no_update

from components.cards import (
    page_header, section_title, footer, kpi_card,
    chart_card, recommendation_box, control_card, alert,
)
from components.charts import pareto_front, scenarios_comparison, COLORS
from components.icons import icon
from components.topbar import topbar
from core.optimizer import lancer_optimisation, identifier_points_caracteristiques


dash.register_page(__name__, path="/optimization", name="Module Optimisation", order=7)


layout = html.Div([
    topbar(["SAD LATRECA", "Modules", "Optimisation"]),

    page_header("target", "Module Optimisation",
                "Recherche multi-objectifs · production vs consommation énergétique",
                badge="MODULE · LIVE", pill="NSGA-II"),

    # Controls
    section_title("Paramètres de recherche"),
    control_card([
        html.Div(className="control-row", children=[
            html.Div([
                html.Label([
                    html.Span("Population"),
                    html.Span(id="opt-pop-display",
                              className="control-value", children="40"),
                ], style={"display": "flex", "justify-content": "space-between"}),
                dcc.Slider(id="opt-pop", min=20, max=120, value=40, step=10,
                            tooltip=None),
            ]),
            html.Div([
                html.Label([
                    html.Span("Générations"),
                    html.Span(id="opt-gen-display",
                              className="control-value", children="20"),
                ], style={"display": "flex", "justify-content": "space-between"}),
                dcc.Slider(id="opt-gen", min=10, max=80, value=20, step=5,
                            tooltip=None),
            ]),
        ]),
        html.Div(style={"text-align": "center", "margin-top": "16px"}, children=[
            html.Button(
                [icon("zap"), "  Lancer l'optimisation"],
                id="btn-launch-opt",
                className="btn btn-gold btn-large",
                n_clicks=0,
            ),
        ]),
        html.Div(style={"margin-top": "10px", "text-align": "center",
                        "color": "#8A9690", "font-size": "12px"},
                  children="Le calcul peut prendre 30 secondes à 2 minutes."),
    ]),

    # Results storage
    dcc.Store(id="opt-results-store"),
    dcc.Loading(
        id="opt-loading",
        type="circle",
        color=COLORS["gold"],
        children=html.Div(id="opt-results-container"),
    ),

    footer(),
])


@callback(
    Output("opt-pop-display", "children"),
    Input("opt-pop", "value"),
)
def upd_pop(v):
    return f"{int(v)} individus"


@callback(
    Output("opt-gen-display", "children"),
    Input("opt-gen", "value"),
)
def upd_gen(v):
    return f"{int(v)} générations"


@callback(
    Output("opt-results-store", "data"),
    Input("btn-launch-opt", "n_clicks"),
    [State("config-store", "data"),
     State("opt-pop", "value"),
     State("opt-gen", "value")],
    prevent_initial_call=True,
)
def lancer_opt(n_clicks, config, pop, gen):
    if not n_clicks:
        return no_update

    if not config:
        config = {
            "K": 335.0, "n": 0.50,
            "d_0": 8.0, "d_f": 2.0, "n_passes": 9,
            "beta": 0.25, "gamma": 1e-6, "Q_lub": 70000.0,
            "T_ambient_C": 25.0, "age_lubrifiant_jours": 30,
        }

    parametres_fixes = {
        'K': config.get('K', 335.0),
        'n': config.get('n', 0.50),
        'd_0': config.get('d_0', 8.0),
        'd_f': config.get('d_f', 2.0),
        'n_passes': int(config.get('n_passes', 9)),
        'beta': config.get('beta', 0.30),
        'gamma': config.get('gamma', 1.5e-6),
        'Q_lub': config.get('Q_lub', 65000.0),
        'T_ambient_C': config.get('T_ambient_C', 25.0),
        'age_lubrifiant_jours': config.get('age_lubrifiant_jours', 30),
        'T_shift_h': config.get('T_shift_h', 8.0),
        'eta_OEE': config.get('eta_OEE', 0.75),
    }

    try:
        resultat = lancer_optimisation(
            parametres_fixes,
            taille_population=int(pop),
            n_generations=int(gen),
            afficher_progression=False,
        )
        points = identifier_points_caracteristiques(resultat['pareto_solutions'])

        return {
            "solutions": resultat['pareto_solutions'],
            "n_solutions": resultat['n_solutions_pareto'],
            "n_evaluations": resultat['n_evaluations'],
            "temps": resultat['temps_calcul_s'],
            "boost": points['boost'],
            "eco": points['eco'],
            "compromis": points['compromis'],
        }
    except Exception as e:
        return {"error": str(e)}


@callback(
    Output("opt-results-container", "children"),
    Input("opt-results-store", "data"),
)
def afficher_resultats(data):
    if not data:
        return html.Div(style={"text-align": "center", "padding": "60px",
                                "color": "#8A9690"},
                         children=[
            icon("chart"),
            html.Div("Lancez l'optimisation pour découvrir les configurations optimales.",
                      style={"margin-top": "12px", "font-size": "14px"}),
        ])

    if "error" in data:
        return alert("danger", "Erreur d'optimisation",
                      data["error"], icon_name="alert")

    if data.get("n_solutions", 0) == 0:
        return alert("warning", "Aucune solution trouvée",
                      "Aucune configuration ne respecte les contraintes. "
                      "Modifiez les paramètres et relancez.",
                      icon_name="alert")

    boost = data["boost"]
    eco = data["eco"]
    compromis = data["compromis"]
    solutions = data["solutions"]

    # KPIs des 3 points
    kpis = [
        kpi_card("trend-up", "Performance",
                 f"{boost['Z1_production_t_jour']:.1f}", unit=" t/j",
                 trend="production max", trend_type="up",
                 footer=f"SEC : {boost['Z2_SEC_kWh_tonne']:.0f} kWh/t"),
        kpi_card("shield", "Compromis",
                 f"{compromis['Z1_production_t_jour']:.1f}", unit=" t/j",
                 trend="équilibré", trend_type="flat",
                 footer=f"SEC : {compromis['Z2_SEC_kWh_tonne']:.0f} kWh/t",
                 dark=True),
        kpi_card("drop", "Économie",
                 f"{eco['Z2_SEC_kWh_tonne']:.0f}", unit=" kWh/t",
                 trend="SEC min", trend_type="down",
                 footer=f"Production : {eco['Z1_production_t_jour']:.1f} t/j"),
        kpi_card("check", "Solutions Pareto",
                 f"{data['n_solutions']}",
                 trend=f"{data['n_evaluations']} évals",
                 trend_type="up",
                 footer=f"Calcul : {data['temps']:.1f} s"),
    ]

    # Front de Pareto avec 3 reperes contextuels
    points_remarquables = {
        "boost": boost,
        "compromis": compromis,
        "eco": eco,
    }
    fig_pareto = pareto_front(
        solutions,
        points_remarquables,
        point_actuel={"Z1": eco['Z1_production_t_jour'] * 0.8,
                       "Z2": boost['Z2_SEC_kWh_tonne'] * 1.1},
        point_reference={"Z1": 25.0, "Z2": 250.0},
    )

    # Comparaison scénarios
    scenarios = {
        "Performance": {"Z1": boost['Z1_production_t_jour'],
                          "Z2": boost['Z2_SEC_kWh_tonne']},
        "Compromis": {"Z1": compromis['Z1_production_t_jour'],
                       "Z2": compromis['Z2_SEC_kWh_tonne']},
        "Économie": {"Z1": eco['Z1_production_t_jour'],
                       "Z2": eco['Z2_SEC_kWh_tonne']},
    }
    fig_scen = scenarios_comparison(scenarios)

    # Tableau des configurations recommandées
    table_data = []
    for nom, point in [("Performance", boost), ("Compromis", compromis),
                        ("Économie", eco)]:
        table_data.append({
            "Scénario": nom,
            "Production (t/j)": f"{point['Z1_production_t_jour']:.2f}",
            "Consommation (kWh/t)": f"{point['Z2_SEC_kWh_tonne']:.1f}",
            "Vitesse (m/s)": f"{point['v_f']:.2f}",
            "μ initial": f"{point['mu_0']:.4f}",
            "Angle moyen (°)": f"{sum(point['alphas'])/len(point['alphas']):.1f}",
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

    rec = recommendation_box(
        "Recommandation stratégique",
        f"Le scénario Compromis offre {compromis['Z1_production_t_jour']:.1f} t/j "
        f"avec une consommation de {compromis['Z2_SEC_kWh_tonne']:.0f} kWh/t. "
        f"Pour maximiser la production, le scénario Performance permet d'atteindre "
        f"{boost['Z1_production_t_jour']:.1f} t/j. "
        f"Pour minimiser les coûts énergétiques, choisissez le scénario Économie "
        f"({eco['Z2_SEC_kWh_tonne']:.0f} kWh/t)."
    )

    return html.Div([
        html.Div(className="kpi-grid", children=kpis,
                  style={"margin-top": "20px"}),

        section_title("Front de Pareto", meta=f"{data['n_solutions']} solutions"),
        chart_card("Configurations optimales (production vs consommation)",
                    dcc.Graph(figure=fig_pareto,
                              config={"displayModeBar": False})),

        section_title("Comparaison des scénarios"),
        chart_card("Performance par stratégie",
                    dcc.Graph(figure=fig_scen,
                              config={"displayModeBar": False})),

        section_title("Configurations recommandées"),
        table,

        rec,
    ])
