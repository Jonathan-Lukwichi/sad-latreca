"""Page 08 - Analyse globale (3 voies + recommandations intelligentes + export PDF)"""

import dash
from dash import html, dcc, Input, Output, State, callback, no_update

from components.cards import (
    page_header, section_title, footer,
    chart_card, recommendation_box, alert,
)
from components.charts import scenarios_comparison
from components.icons import icon
from components.topbar import topbar
from core.coupled_solver import simuler_scenario
from core.optimizer import lancer_optimisation, identifier_points_caracteristiques
from core.recommendations import diagnostic_global


dash.register_page(__name__, path="/analysis", name="Analyse globale", order=8)


# Reference constructeur (cible)
REFERENCE = {
    "vitesse": 20.0,
    "production": 25.0,
    "consommation": 250.0,
    "maintenance": 30,
    "temperature": 75.0,
}


def comparison_card(side, title, status_label, status_type, rows):
    """Carte de diagnostic (Actuelle / Optimisation / Reference)."""
    icon_name = {"actual": "info", "optim": "target",
                  "reference": "check"}.get(side, "info")
    return html.Div(
        className=f"diagnostic-card diag-{side}",
        children=[
            html.Div(
                className="diagnostic-head",
                children=[
                    html.Div(
                        className="diag-title",
                        children=[
                            icon(icon_name),
                            html.Span(title),
                        ],
                    ),
                    html.Span(
                        status_label,
                        className=f"diag-pill diag-pill-{status_type}",
                    ),
                ],
            ),
            html.Div(
                className="diagnostic-rows",
                children=[
                    html.Div(
                        className="diag-row",
                        children=[
                            html.Span(label, className="diag-row-label"),
                            html.Span(value, className="diag-row-value"),
                        ],
                    )
                    for label, value in rows
                ],
            ),
        ],
    )


def ecart_bar_3way(label, unit, actuel, optim, reference):
    """Barre d'ecart actuel / optim / reference (3 voies)."""
    vals = [abs(actuel), abs(optim) if optim is not None else 0,
            abs(reference)]
    max_val = max(vals) * 1.05 if max(vals) > 0 else 1.0

    pct_actuel = (abs(actuel) / max_val) * 100
    pct_ref = (abs(reference) / max_val) * 100
    pct_optim = (abs(optim) / max_val) * 100 if optim is not None else 0

    ecart_pct = (actuel - reference) / reference * 100 if reference else 0
    badge_type = "danger" if abs(ecart_pct) > 15 else "warning"
    sign = "+" if ecart_pct > 0 else ""

    rows = [
        html.Div(className="ecart-row", children=[
            html.Span("ACTUEL", className="ecart-row-label"),
            html.Div(className="ecart-bar-track", children=html.Div(
                className="ecart-bar-fill ecart-bar-actual",
                style={"width": f"{pct_actuel}%"})),
            html.Span(f"{actuel:.0f}", className="ecart-row-value"),
        ]),
    ]
    if optim is not None:
        rows.append(html.Div(className="ecart-row", children=[
            html.Span("OPTIM.", className="ecart-row-label"),
            html.Div(className="ecart-bar-track", children=html.Div(
                className="ecart-bar-fill ecart-bar-optim",
                style={"width": f"{pct_optim}%"})),
            html.Span(f"{optim:.0f}", className="ecart-row-value"),
        ]))
    rows.append(html.Div(className="ecart-row", children=[
        html.Span("RÉF.", className="ecart-row-label"),
        html.Div(className="ecart-bar-track", children=html.Div(
            className="ecart-bar-fill ecart-bar-reference",
            style={"width": f"{pct_ref}%"})),
        html.Span(f"{reference:.0f}", className="ecart-row-value"),
    ]))

    return html.Div(
        className="ecart-block",
        children=[
            html.Div(className="ecart-header", children=[
                html.Span(className="ecart-title", children=[
                    html.Strong(label),
                    html.Span(f" · {unit}", className="ecart-unit"),
                ]),
                html.Span(f"{sign}{ecart_pct:.0f} %",
                          className=f"ecart-badge ecart-badge-{badge_type}"),
            ]),
            *rows,
        ],
    )


def render_action_card(action):
    """Carte pour une action recommandee (sortie du moteur intelligent)."""
    sev = action.get("severite", "ok")
    color = {"critique": "danger", "vigilance": "warning",
             "ok": "success"}.get(sev, "neutral")
    return html.Div(
        className=f"action-card action-card-{color}",
        style={
            "padding": "14px 16px",
            "border-radius": "12px",
            "border": "1px solid #E5DFCE",
            "background": "#FFFFFF",
            "margin-bottom": "10px",
        },
        children=[
            html.Div(style={"display": "flex",
                            "justify-content": "space-between",
                            "align-items": "center", "margin-bottom": "6px"},
                     children=[
                html.Div(style={"display": "flex", "align-items": "center",
                                "gap": "8px"}, children=[
                    html.Span(action.get("module", ""),
                              style={"font-family": "JetBrains Mono",
                                     "font-size": "10px",
                                     "color": "#8A9690",
                                     "text-transform": "uppercase",
                                     "letter-spacing": "0.08em"}),
                    html.Strong(action.get("titre", ""),
                                style={"color": "#0A2A1F"}),
                ]),
                html.Span(sev.upper(),
                          className=f"section-pill section-pill-{color}"),
            ]),
            html.Div(action.get("constat", ""),
                     style={"color": "#3D4F47", "font-size": "13px",
                            "margin-bottom": "8px"}),
            html.Ul([
                html.Li(a, style={"font-size": "13px",
                                  "color": "#0A2A1F",
                                  "margin-bottom": "4px"})
                for a in action.get("actions", [])
            ], style={"padding-left": "20px", "margin": "6px 0"}),
            html.Div(
                f"Gain estimé : {action.get('gain_estime', '—')}",
                style={"font-family": "JetBrains Mono", "font-size": "11px",
                       "color": "#A38B3E", "margin-top": "6px"}
            ),
        ],
    )


layout = html.Div([
    topbar(["SAD LATRECA", "Diagnostic", "Analyse globale"]),

    page_header("line-chart", "Analyse globale",
                "Diagnostic 3 voies (Actuelle / Optimisation / Référence) · "
                "recommandations intelligentes · export PDF",
                badge="DIAGNOSTIC", pill="Live"),

    # Stocke le resultat NSGA-II local a cette page
    dcc.Store(id="analysis-opt-store"),

    # Bouton lancer optimisation
    section_title("Optimisation NSGA-II",
                  meta="comparaison automatique avec la config courante"),
    html.Div(style={"display": "grid",
                    "grid-template-columns": "1fr auto",
                    "gap": "12px", "align-items": "center",
                    "padding": "14px 18px", "background": "#FFFFFF",
                    "border": "1px solid #E5DFCE",
                    "border-radius": "14px",
                    "margin-bottom": "16px"}, children=[
        html.Div([
            html.Div("Lancer une optimisation NSGA-II rapide depuis cette page",
                     style={"color": "#0A2A1F", "font-weight": "600"}),
            html.Div("La 3e voie 'Optimisation' apparaitra dans tous les "
                     "blocs ci-dessous (Population 40 · Générations 25 · "
                     "~30 secondes).",
                     style={"color": "#8A9690", "font-size": "12px"}),
        ]),
        html.Button(
            [icon("zap"), "  Lancer optimisation"],
            id="btn-analysis-launch-opt",
            className="btn btn-gold",
            n_clicks=0,
        ),
    ]),
    dcc.Loading(
        id="analysis-opt-loading",
        type="circle",
        color="#A38B3E",
        children=html.Div(id="analysis-opt-status",
                           style={"margin-bottom": "16px"}),
    ),

    # Diagnostic 3 voies
    section_title("Diagnostic actuel vs optimisation vs référence",
                  meta="3 voies"),
    html.Div(id="analysis-diagnostic", className="diagnostic-grid"),

    # Ecarts
    section_title("Écarts de performance", meta="3 indicateurs"),
    html.Div(id="analysis-ecarts", className="ecarts-card"),

    # Comparaison scenarios chart
    section_title("Comparaison de scénarios"),
    chart_card("Performance par stratégie",
               dcc.Graph(id="analysis-chart-scen",
                         config={"displayModeBar": False})),

    # Recommandations intelligentes
    section_title("Actions recommandées", meta="moteur intelligent"),
    html.Div(id="analysis-actions",
             style={"margin-bottom": "16px"}),

    # Verdict synthetique
    html.Div(id="analysis-recommendation"),

    # Export
    section_title("Export du rapport"),
    html.Div(style={"display": "grid",
                    "grid-template-columns": "1fr 1fr 1fr",
                    "gap": "12px", "margin-bottom": "24px"}, children=[
        html.Button([icon("download"), "  Télécharger CSV"],
                    id="btn-export-csv", className="btn btn-secondary"),
        html.Button([icon("download"), "  Télécharger JSON"],
                    id="btn-export-json", className="btn btn-secondary"),
        html.Button([icon("download"), "  Rapport PDF complet"],
                    id="btn-export-pdf", className="btn btn-gold"),
    ]),
    dcc.Loading(
        id="pdf-loading", type="circle", color="#A38B3E",
        children=html.Div(id="pdf-status",
                           style={"margin-bottom": "12px"}),
    ),
    dcc.Download(id="download-csv"),
    dcc.Download(id="download-json"),
    dcc.Download(id="download-pdf"),

    footer(),
])


# ═══════════════════════════════════════════════════════════════════
# Callback : lancement optimisation depuis cette page
# ═══════════════════════════════════════════════════════════════════

@callback(
    [Output("analysis-opt-store", "data"),
     Output("analysis-opt-status", "children"),
     Output("opt-global-store", "data", allow_duplicate=True),
     Output("last-analysis-store", "data", allow_duplicate=True)],
    Input("btn-analysis-launch-opt", "n_clicks"),
    State("config-store", "data"),
    prevent_initial_call=True,
)
def launch_opt_from_analysis(n_clicks, config):
    if not n_clicks:
        return no_update, no_update, no_update, no_update
    config = config or {}

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
    }

    try:
        from datetime import datetime
        res = lancer_optimisation(parametres_fixes,
                                    taille_population=40,
                                    n_generations=25,
                                    afficher_progression=False)
        points = identifier_points_caracteristiques(res['pareto_solutions'])
        store = {
            "n_solutions": res['n_solutions_pareto'],
            "n_evaluations": res['n_evaluations'],
            "temps": res['temps_calcul_s'],
            "boost": points['boost'],
            "eco": points['eco'],
            "compromis": points['compromis'],
        }
        ts = datetime.now().isoformat()
        if res['n_solutions_pareto'] == 0:
            warn = alert("warning", "Aucune solution Pareto trouvée",
                          "Relachez les contraintes (η_cooling plus eleve, "
                          "ou T_max plus permissif).", icon_name="alert")
            return store, warn, store, ts
        msg = (f"{res['n_solutions_pareto']} solutions Pareto · "
               f"{res['n_evaluations']} evaluations · "
               f"{res['temps_calcul_s']:.1f}s")
        ok = alert("success", "Optimisation terminée", msg, icon_name="check")
        return store, ok, store, ts
    except Exception as e:
        err = alert("danger", "Erreur d'optimisation",
                     str(e), icon_name="alert")
        return None, err, no_update, no_update


# ═══════════════════════════════════════════════════════════════════
# Callback : mise a jour du diagnostic complet (declenchee par config OU optim)
# ═══════════════════════════════════════════════════════════════════

@callback(
    [Output("analysis-diagnostic", "children"),
     Output("analysis-ecarts", "children"),
     Output("analysis-chart-scen", "figure"),
     Output("analysis-actions", "children"),
     Output("analysis-recommendation", "children")],
    [Input("config-store", "data"),
     Input("analysis-opt-store", "data")],
)
def update_analysis(store, opt_store):
    store = store or {}
    try:
        resultat = simuler_scenario(store)
    except Exception as e:
        return (None, None, {}, None,
                alert("danger", "Erreur", str(e), "alert"))

    kpis_data = resultat['KPIs']

    v_actuel = float(store.get('v_f', 15.0))
    prod_actuel = float(kpis_data['Z1_production_t_jour'])
    sec_actuel = float(kpis_data['Z2_SEC_kWh_tonne'])
    age_lub = int(store.get('age_lubrifiant_jours', 30))
    T_actuel = float(kpis_data['T_max_C'])
    T_seuil = float(store.get('T_max_C', 140.0))

    sous_perf = (prod_actuel < REFERENCE['production'] * 0.95
                  or sec_actuel > REFERENCE['consommation'] * 1.05)

    # Optimisation : extraire compromis si disponible
    compromis = (opt_store or {}).get('compromis') if opt_store else None
    has_opt = compromis is not None

    # Cartes diagnostic (2 ou 3 selon disponibilite optim)
    diagnostic = [
        comparison_card(
            "actual", "Conditions actuelles",
            "Sous-performance" if sous_perf else "Conforme",
            "danger" if sous_perf else "success",
            [
                ("Vitesse de ligne", f"{v_actuel:.1f} m/s"),
                ("Production", f"{prod_actuel:.1f} t/jour"),
                ("Consommation", f"{sec_actuel:.0f} kWh/t"),
                ("Âge lubrifiant", f"{age_lub} jours"),
                ("Température max", f"{T_actuel:.1f} °C"),
            ],
        ),
    ]

    if has_opt:
        diagnostic.append(comparison_card(
            "optim", "Optimisation NSGA-II",
            "Compromis Pareto", "warning",
            [
                ("Vitesse optimale",
                 f"{compromis['v_f']:.1f} m/s"),
                ("Production",
                 f"{compromis['Z1_production_t_jour']:.1f} t/jour"),
                ("Consommation",
                 f"{compromis['Z2_SEC_kWh_tonne']:.0f} kWh/t"),
                ("μ₀ optimal",
                 f"{compromis['mu_0']:.3f}"),
                ("α moyen",
                 f"{(sum(compromis['alphas'])/len(compromis['alphas'])):.1f}°"),
            ],
        ))

    diagnostic.append(comparison_card(
        "reference", "Référence constructeur", "Cible", "success",
        [
            ("Vitesse nominale", f"{REFERENCE['vitesse']:.1f} m/s"),
            ("Production nominale",
             f"{REFERENCE['production']:.1f} t/jour"),
            ("Consommation nominale",
             f"{REFERENCE['consommation']:.0f} kWh/t"),
            ("Maintenance recommandée",
             f"{REFERENCE['maintenance']} jours"),
            ("Température cible",
             f"≤ {REFERENCE['temperature']:.1f} °C"),
        ],
    ))

    # Ecarts 3 voies
    optim_v = compromis['v_f'] if has_opt else None
    optim_prod = compromis['Z1_production_t_jour'] if has_opt else None
    optim_sec = compromis['Z2_SEC_kWh_tonne'] if has_opt else None

    ecarts = [
        ecart_bar_3way("Vitesse", "m/s",
                        v_actuel, optim_v, REFERENCE['vitesse']),
        ecart_bar_3way("Production", "t/jour",
                        prod_actuel, optim_prod, REFERENCE['production']),
        ecart_bar_3way("Consommation", "kWh/t",
                        sec_actuel, optim_sec, REFERENCE['consommation']),
    ]

    # Comparaison scenarios chart (2 ou 3 barres)
    scenarios = {
        "Actuel": {"Z1": prod_actuel, "Z2": sec_actuel},
    }
    if has_opt:
        scenarios["Optimisation"] = {
            "Z1": compromis['Z1_production_t_jour'],
            "Z2": compromis['Z2_SEC_kWh_tonne'],
        }
    scenarios["Référence"] = {
        "Z1": REFERENCE['production'],
        "Z2": REFERENCE['consommation'],
    }
    fig_scen = scenarios_comparison(scenarios)

    # Moteur de recommandations intelligent
    diag = diagnostic_global(resultat, REFERENCE,
                              opt_store, T_seuil=T_seuil)
    actions_html = ([render_action_card(a) for a in diag['actions']]
                     if diag['actions'] else
                     [alert("success", "Aucune action requise",
                             "Tous les modules sont en zone optimale.",
                             icon_name="check")])

    # Verdict synthetique
    sev = diag['severite_globale']
    rec_type = {"critique": "danger", "vigilance": "warning",
                "ok": "success"}.get(sev, "neutral")
    rec = html.Div([
        alert(rec_type, "Verdict", diag['verdict'],
              icon_name="alert" if sev != "ok" else "check"),
        recommendation_box(
            "Prochaine étape",
            ("Téléchargez le rapport PDF complet pour archivage et "
             "présentation à la direction LATRECA.")
            if has_opt else
            ("Lancez l'optimisation NSGA-II ci-dessus pour comparer "
             "votre configuration actuelle avec la meilleure solution "
             "Pareto identifiée par l'algorithme.")
        ),
    ])

    return diagnostic, ecarts, fig_scen, actions_html, rec


# ═══════════════════════════════════════════════════════════════════
# Export CSV
# ═══════════════════════════════════════════════════════════════════

@callback(
    Output("download-csv", "data"),
    Input("btn-export-csv", "n_clicks"),
    State("config-store", "data"),
    prevent_initial_call=True,
)
def export_csv(n_clicks, store):
    if not n_clicks:
        return None
    store = store or {}
    try:
        resultat = simuler_scenario(store)
    except Exception:
        return None

    n_passes = len(resultat['delta_T'])
    lines = ["Etape,Diametre_mm,Vitesse_m_s,Force_N,Puissance_kW,DeltaT_C,T_cumulee_C,mu"]
    for i in range(n_passes):
        lines.append(
            f"{i+1},{resultat['diametres'][i+1]:.3f},"
            f"{resultat['vitesses'][i]:.3f},{resultat['forces'][i]:.1f},"
            f"{resultat['puissances'][i]/1000:.3f},"
            f"{resultat['delta_T'][i]:.2f},"
            f"{resultat['temperatures'][i+1]:.2f},"
            f"{resultat['mu_par_passe'][i]:.5f}"
        )
    return dict(content="\n".join(lines), filename="sad_analyse.csv")


# ═══════════════════════════════════════════════════════════════════
# Export JSON
# ═══════════════════════════════════════════════════════════════════

@callback(
    Output("download-json", "data"),
    Input("btn-export-json", "n_clicks"),
    [State("config-store", "data"),
     State("analysis-opt-store", "data")],
    prevent_initial_call=True,
)
def export_json(n_clicks, store, opt_store):
    if not n_clicks:
        return None
    store = store or {}
    try:
        resultat = simuler_scenario(store)
    except Exception:
        return None

    import json
    import numpy as np

    def _to_py(obj):
        """Convertit recursivement les types numpy/np.bool en types Python natifs."""
        if isinstance(obj, dict):
            return {k: _to_py(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_to_py(v) for v in obj]
        if isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    payload = _to_py({
        "configuration": store,
        "KPIs": resultat['KPIs'],
        "securite": {
            "C1_mecanique_ok": resultat['securite']['C1_mecanique']['ok'],
            "C2_thermique_ok": resultat['securite']['C2_thermique']
                                          ['securite_ok'],
            "C3_moteur_ok": resultat['securite']['C3_moteur']['ok'],
            "C4_tribologique_ok": resultat['securite']['C4_tribologique']
                                            ['ok'],
            "tout_ok": resultat['securite']['tout_ok'],
        },
        "details_par_passe": {
            "diametres": resultat['diametres'],
            "vitesses": resultat['vitesses'],
            "forces": resultat['forces'],
            "puissances_W": resultat['puissances'],
            "delta_T": resultat['delta_T'],
            "temperatures": resultat['temperatures'],
            "mu_par_passe": resultat['mu_par_passe'],
        },
        "optimisation": opt_store,
    })
    return dict(content=json.dumps(payload, indent=2),
                 filename="sad_analyse.json")


# ═══════════════════════════════════════════════════════════════════
# Export PDF (rapport complet)
# ═══════════════════════════════════════════════════════════════════

@callback(
    [Output("download-pdf", "data"),
     Output("pdf-status", "children")],
    Input("btn-export-pdf", "n_clicks"),
    [State("config-store", "data"),
     State("analysis-opt-store", "data")],
    prevent_initial_call=True,
)
def export_pdf(n_clicks, store, opt_store):
    if not n_clicks:
        return no_update, no_update

    store = store or {}
    try:
        resultat = simuler_scenario(store)
    except Exception as e:
        return None, alert("danger", "Erreur", str(e), "alert")

    try:
        from core.pdf_export import generer_rapport_pdf
        pdf_bytes = generer_rapport_pdf(store, resultat,
                                          opt_store, REFERENCE)
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        return (dict(content=pdf_bytes, filename=f"sad_latreca_rapport_{ts}.pdf",
                     base64=True, type="application/pdf"),
                alert("success", "Rapport PDF généré",
                      "Téléchargement lancé.", icon_name="check"))
    except Exception as e:
        return None, alert("danger", "Erreur PDF", str(e), "alert")
