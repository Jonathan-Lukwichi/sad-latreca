"""Page 07 - Module Optimisation"""

import dash
from dash import html, dcc, Input, Output, State, callback, dash_table, no_update

from components.cards import (
    page_header, section_title, footer, kpi_card,
    chart_card, recommendation_box, control_card, alert,
)
from components.charts import (pareto_front, scenarios_comparison,
                                  convergence_chart, COLORS)
from components.icons import icon
from components.topbar import topbar
from core.optimizer import lancer_optimisation, identifier_points_caracteristiques
from core.coupled_solver import simuler_scenario


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

    # Contraintes manuelles (expert mode)
    section_title("Contraintes de sécurité (mode expert)",
                  meta="ajustables manuellement"),
    control_card([
        html.Div(style={"margin-bottom": "10px", "color": "#8A9690",
                        "font-size": "12px"},
                 children=("Les seuils ci-dessous bornent l'espace de recherche "
                           "NSGA-II. Relachez-les pour explorer davantage de "
                           "configurations, resserrez-les pour une securite accrue.")),
        html.Div(className="control-row", children=[
            html.Div([
                html.Label([
                    html.Span("Seuil thermique T_max (tréfilage humide LATRECA)"),
                    html.Span(id="opt-c-tmax-display",
                              className="control-value", children="140 °C"),
                ], style={"display": "flex", "justify-content": "space-between"}),
                dcc.Slider(id="opt-c-tmax", min=20, max=140, value=140, step=5,
                           tooltip=None),
            ]),
            html.Div([
                html.Label([
                    html.Span("Marge mécanique σ_d/σ_y max"),
                    html.Span(id="opt-c-sigma-display",
                              className="control-value", children="0.60"),
                ], style={"display": "flex", "justify-content": "space-between"}),
                dcc.Slider(id="opt-c-sigma", min=0.30, max=0.85, value=0.60, step=0.05,
                           tooltip=None),
            ]),
        ]),
        html.Div(className="control-row", children=[
            html.Div([
                html.Label([
                    html.Span("Puissance moteur nominale"),
                    html.Span(id="opt-c-pmot-display",
                              className="control-value", children="200 kW"),
                ], style={"display": "flex", "justify-content": "space-between"}),
                dcc.Slider(id="opt-c-pmot", min=50, max=500, value=200, step=25,
                           tooltip=None),
            ]),
            html.Div([
                html.Label([
                    html.Span("Facteur μ critique (×μ₀)"),
                    html.Span(id="opt-c-mufac-display",
                              className="control-value", children="1.50"),
                ], style={"display": "flex", "justify-content": "space-between"}),
                dcc.Slider(id="opt-c-mufac", min=1.10, max=2.50, value=1.50, step=0.10,
                           tooltip=None),
            ]),
        ]),
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


@callback(Output("opt-c-tmax-display", "children"), Input("opt-c-tmax", "value"))
def _disp_tmax(v):
    return f"{int(v)} °C" if v is not None else "—"


@callback(Output("opt-c-sigma-display", "children"), Input("opt-c-sigma", "value"))
def _disp_sigma(v):
    return f"{v:.2f}" if v is not None else "—"


@callback(Output("opt-c-pmot-display", "children"), Input("opt-c-pmot", "value"))
def _disp_pmot(v):
    return f"{int(v)} kW" if v is not None else "—"


@callback(Output("opt-c-mufac-display", "children"), Input("opt-c-mufac", "value"))
def _disp_mufac(v):
    return f"{v:.2f}" if v is not None else "—"


@callback(
    Output("opt-results-store", "data"),
    Input("btn-launch-opt", "n_clicks"),
    [State("config-store", "data"),
     State("opt-pop", "value"),
     State("opt-gen", "value"),
     State("opt-c-tmax", "value"),
     State("opt-c-sigma", "value"),
     State("opt-c-pmot", "value"),
     State("opt-c-mufac", "value")],
    prevent_initial_call=True,
)
def lancer_opt(n_clicks, config, pop, gen, c_tmax, c_sigma, c_pmot, c_mufac):
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
        'eta_cooling': config.get('eta_cooling', 0.6),
        # Surcharges des seuils de contraintes (mode expert)
        'T_max_C': float(c_tmax) if c_tmax is not None else 140.0,
        'sigma_safety_factor': float(c_sigma) if c_sigma is not None else 0.60,
        'P_moteur_nominal': float(c_pmot) if c_pmot is not None else 200.0,
        'mu_critique_factor': float(c_mufac) if c_mufac is not None else 1.50,
    }

    # ─── BASELINE : simuler la config courante AVANT NSGA-II ───
    # Permet a l'utilisateur de voir l'amelioration reelle apres optimisation.
    baseline = None
    try:
        baseline_params = {
            **parametres_fixes,
            'v_f': float(config.get('v_f', 15.0)),
            'mu_0': float(config.get('mu_0', 0.060)),
            'alphas': config.get('alphas', [6.0] * 9),
            'diametres_reels': config.get('diametres_reels'),
        }
        r0 = simuler_scenario(baseline_params)
        baseline = {
            'Z1': float(r0['KPIs']['Z1_production_t_jour']),
            'Z2': float(r0['KPIs']['Z2_SEC_kWh_tonne']),
            'T_max_C': float(r0['KPIs']['T_max_C']),
            'P_kW': float(r0['KPIs']['P_totale_kW']),
            'F_max_N': float(r0['KPIs']['F_max_N']),
            'mu_max': float(r0['KPIs']['mu_max']),
            'v_f': float(baseline_params['v_f']),
            'mu_0': float(baseline_params['mu_0']),
            'tout_ok': bool(r0['securite']['tout_ok']),
        }
    except Exception:
        baseline = None

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
            "history": resultat.get('history'),
            "baseline": baseline,
        }
    except Exception as e:
        return {"error": str(e), "baseline": baseline}


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
    baseline = data.get("baseline")

    # ─── Bloc BASELINE → OPTIMISE (Avant / Apres) ───
    avant_apres_section = []
    if baseline is not None:
        b_z1 = baseline['Z1']
        b_z2 = baseline['Z2']
        c_z1 = compromis['Z1_production_t_jour']
        c_z2 = compromis['Z2_SEC_kWh_tonne']

        gain_z1_pct = ((c_z1 - b_z1) / b_z1 * 100) if b_z1 > 0 else 0
        gain_z2_pct = ((b_z2 - c_z2) / b_z2 * 100) if b_z2 > 0 else 0

        # KPI cards Avant/Apres
        avant_apres_kpis = html.Div(
            className="kpi-grid",
            style={"margin-top": "20px"},
            children=[
                kpi_card("info", "AVANT · Production",
                         f"{b_z1:.2f}", unit=" t/j",
                         trend="config courante", trend_type="flat",
                         footer=f"v_f = {baseline['v_f']:.1f} m/s · "
                                f"μ₀ = {baseline['mu_0']:.3f}"),
                kpi_card("trend-up", "APRÈS · Production",
                         f"{c_z1:.2f}", unit=" t/j",
                         trend=f"+{gain_z1_pct:.0f}%" if gain_z1_pct >= 0
                               else f"{gain_z1_pct:.0f}%",
                         trend_type="up" if gain_z1_pct > 0 else "down",
                         footer="scénario Compromis",
                         dark=True),
                kpi_card("info", "AVANT · Consommation",
                         f"{b_z2:.0f}", unit=" kWh/t",
                         trend="config courante", trend_type="flat",
                         footer=f"T_max = {baseline['T_max_C']:.0f} °C"),
                kpi_card("trend-down", "APRÈS · Consommation",
                         f"{c_z2:.0f}", unit=" kWh/t",
                         trend=f"-{gain_z2_pct:.0f}%" if gain_z2_pct >= 0
                               else f"+{abs(gain_z2_pct):.0f}%",
                         trend_type="down" if gain_z2_pct > 0 else "up",
                         footer="scénario Compromis"),
            ],
        )

        # Banniere de synthese
        if gain_z1_pct > 5 or gain_z2_pct > 5:
            banner = alert(
                "success",
                f"Optimisation efficace : +{gain_z1_pct:.0f}% production · "
                f"-{gain_z2_pct:.0f}% consommation",
                f"En passant de votre configuration actuelle "
                f"({b_z1:.2f} t/j, {b_z2:.0f} kWh/t) au scénario Compromis "
                f"NSGA-II ({c_z1:.2f} t/j, {c_z2:.0f} kWh/t), vous gagnez "
                f"{c_z1 - b_z1:+.2f} t/jour de production tout en "
                f"économisant {b_z2 - c_z2:+.0f} kWh/tonne d'énergie.",
                icon_name="check",
            )
        elif gain_z1_pct < -2:
            banner = alert(
                "warning",
                "Optimisation contrainte par les seuils",
                f"Le compromis NSGA-II ({c_z1:.2f} t/j) reste sous votre "
                f"baseline ({b_z1:.2f} t/j). Cela signifie que vos "
                f"contraintes de sécurité actuelles forcent un ralentissement. "
                f"Relâchez T_max ou augmentez η_cooling pour explorer un "
                f"espace plus permissif.",
                icon_name="alert",
            )
        else:
            banner = alert(
                "neutral",
                "Marge d'amélioration limitée",
                "La configuration courante est déjà proche de l'optimum "
                "Pareto. Modifiez les paramètres de configuration pour "
                "tester d'autres scénarios.",
                icon_name="info",
            )

        avant_apres_section = [
            section_title("Avant / Après optimisation",
                          meta="comparaison config courante vs NSGA-II Compromis"),
            avant_apres_kpis,
            banner,
        ]

    # ─── KPIs des 3 scenarios Pareto ───
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

    # ─── Front de Pareto avec le VRAI point baseline ───
    points_remarquables = {
        "boost": boost,
        "compromis": compromis,
        "eco": eco,
    }
    pt_actuel = ({"Z1": baseline['Z1'], "Z2": baseline['Z2']}
                 if baseline else None)
    fig_pareto = pareto_front(
        solutions,
        points_remarquables,
        point_actuel=pt_actuel,
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

    # Tableau des configurations recommandées (avec ligne BASELINE en tete)
    table_data = []
    if baseline is not None:
        # Ligne baseline (config courante de l'utilisateur)
        # Note : pas d'angle moyen car les alphas du store sont uniformes
        table_data.append({
            "Scénario": "● Baseline (votre config)",
            "Production (t/j)": f"{baseline['Z1']:.2f}",
            "Consommation (kWh/t)": f"{baseline['Z2']:.1f}",
            "Vitesse (m/s)": f"{baseline['v_f']:.2f}",
            "μ initial": f"{baseline['mu_0']:.4f}",
            "Angle moyen (°)": "—",
        })
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

    # Recommandation reformulee avec le gain reel vs baseline
    if baseline is not None and baseline['Z1'] > 0:
        gain_perf = ((boost['Z1_production_t_jour'] - baseline['Z1'])
                      / baseline['Z1'] * 100)
        gain_eco = ((baseline['Z2'] - eco['Z2_SEC_kWh_tonne'])
                     / baseline['Z2'] * 100) if baseline['Z2'] > 0 else 0
        gain_compr = ((compromis['Z1_production_t_jour'] - baseline['Z1'])
                       / baseline['Z1'] * 100)
        rec_text = (
            f"À partir de votre baseline ({baseline['Z1']:.2f} t/j, "
            f"{baseline['Z2']:.0f} kWh/t), NSGA-II propose 3 leviers : "
            f"(1) Performance → {boost['Z1_production_t_jour']:.1f} t/j "
            f"({gain_perf:+.0f}% production), "
            f"(2) Compromis → {compromis['Z1_production_t_jour']:.1f} t/j "
            f"({gain_compr:+.0f}%) avec un bon équilibre énergétique, "
            f"(3) Économie → {eco['Z2_SEC_kWh_tonne']:.0f} kWh/t "
            f"({gain_eco:+.0f}% consommation) si l'énergie est prioritaire."
        )
    else:
        rec_text = (
            f"Le scénario Compromis offre "
            f"{compromis['Z1_production_t_jour']:.1f} t/j avec une "
            f"consommation de {compromis['Z2_SEC_kWh_tonne']:.0f} kWh/t. "
            f"Pour maximiser la production, le scénario Performance permet "
            f"d'atteindre {boost['Z1_production_t_jour']:.1f} t/j. "
            f"Pour minimiser les coûts énergétiques, choisissez Économie "
            f"({eco['Z2_SEC_kWh_tonne']:.0f} kWh/t)."
        )
    rec = recommendation_box("Recommandation stratégique", rec_text)

    # Graphique de convergence (si l'historique est disponible)
    history = data.get("history")
    convergence_section = []
    if history and history.get("generation"):
        n_gen = len(history["generation"])
        last_z1 = history["best_Z1"][-1] if history["best_Z1"] else 0
        last_z2 = history["best_Z2"][-1] if history["best_Z2"] else 0
        first_z1 = next((z for z in history["best_Z1"] if z > 0), last_z1)
        gain = ((last_z1 - first_z1) / first_z1 * 100
                if first_z1 > 0 else 0)
        meta_text = (f"{n_gen} générations · "
                      f"gain Z₁ +{gain:.0f}% · "
                      f"convergence finale {last_z1:.1f} t/j ↔ "
                      f"{last_z2:.0f} kWh/t")
        fig_conv = convergence_chart(history)
        convergence_section = [
            section_title("Convergence de l'algorithme", meta=meta_text),
            chart_card(
                "Évolution génération par génération · NSGA-II en action",
                dcc.Graph(figure=fig_conv,
                          config={"displayModeBar": False})),
        ]

    return html.Div([
        # En haut : Avant / Apres optimisation
        *avant_apres_section,

        # Puis les 3 scenarios Pareto
        section_title("Scénarios Pareto identifiés",
                       meta=f"{data['n_solutions']} solutions"),
        html.Div(className="kpi-grid", children=kpis),

        section_title("Front de Pareto",
                       meta=f"{data['n_solutions']} solutions"),
        chart_card("Configurations optimales (production vs consommation)",
                    dcc.Graph(figure=fig_pareto,
                              config={"displayModeBar": False})),

        *convergence_section,

        section_title("Comparaison des scénarios"),
        chart_card("Performance par stratégie",
                    dcc.Graph(figure=fig_scen,
                              config={"displayModeBar": False})),

        section_title("Configurations recommandées",
                       meta="baseline + 3 scénarios Pareto"),
        table,

        rec,
    ])
