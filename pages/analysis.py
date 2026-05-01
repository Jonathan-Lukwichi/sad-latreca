"""Page 08 - Analyse globale"""

import dash
from dash import html, dcc, Input, Output, callback, dash_table

from components.cards import (
    page_header, section_title, footer, kpi_card,
    chart_card, recommendation_box, alert,
)
from components.charts import scenarios_comparison, COLORS
from components.icons import icon
from components.topbar import topbar
from core.coupled_solver import simuler_scenario


dash.register_page(__name__, path="/analysis", name="Analyse globale", order=8)


# Référence constructeur (cible)
REFERENCE = {
    "vitesse": 20.0,
    "production": 25.0,
    "consommation": 250.0,
    "maintenance": 30,
    "temperature": 75.0,
}


def comparison_card(side, title, status_label, status_type, rows):
    """
    Carte de diagnostic (Conditions actuelles vs Référence constructeur).
    side : 'actual' (coral) ou 'reference' (mint)
    """
    return html.Div(
        className=f"diagnostic-card diag-{side}",
        children=[
            html.Div(
                className="diagnostic-head",
                children=[
                    html.Div(
                        className="diag-title",
                        children=[
                            icon("info" if side == "actual" else "check"),
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


def ecart_bar(label, unit, actuel, reference, ecart_pct):
    """Barre d'écart actuel vs référence."""
    # Échelle commune (max des deux)
    max_val = max(abs(actuel), abs(reference)) * 1.05 if max(abs(actuel), abs(reference)) > 0 else 1
    pct_actuel = (abs(actuel) / max_val) * 100
    pct_ref = (abs(reference) / max_val) * 100

    # Type d'ecart : negatif = sous-perf (coral), positif sur conso = mauvais (coral)
    badge_type = "danger" if abs(ecart_pct) > 15 else "warning"
    sign = "+" if ecart_pct > 0 else ""

    return html.Div(
        className="ecart-block",
        children=[
            html.Div(
                className="ecart-header",
                children=[
                    html.Span(
                        className="ecart-title",
                        children=[
                            html.Strong(label),
                            html.Span(f" · {unit}", className="ecart-unit"),
                        ],
                    ),
                    html.Span(
                        f"{sign}{ecart_pct:.0f} %",
                        className=f"ecart-badge ecart-badge-{badge_type}",
                    ),
                ],
            ),
            html.Div(
                className="ecart-row",
                children=[
                    html.Span("ACTUEL", className="ecart-row-label"),
                    html.Div(
                        className="ecart-bar-track",
                        children=html.Div(
                            className="ecart-bar-fill ecart-bar-actual",
                            style={"width": f"{pct_actuel}%"},
                        ),
                    ),
                    html.Span(f"{actuel:.0f}", className="ecart-row-value"),
                ],
            ),
            html.Div(
                className="ecart-row",
                children=[
                    html.Span("RÉF.", className="ecart-row-label"),
                    html.Div(
                        className="ecart-bar-track",
                        children=html.Div(
                            className="ecart-bar-fill ecart-bar-reference",
                            style={"width": f"{pct_ref}%"},
                        ),
                    ),
                    html.Span(f"{reference:.0f}", className="ecart-row-value"),
                ],
            ),
        ],
    )


layout = html.Div([
    topbar(["SAD LATRECA", "Diagnostic", "Analyse globale"]),

    page_header("line-chart", "Analyse globale",
                "Diagnostic, comparaison de scénarios et export des rapports",
                badge="DIAGNOSTIC", pill="3 écarts critiques", pill_type="danger"),

    # Diagnostic actuel vs reference
    section_title("Diagnostic actuel vs référence", meta="mise à jour il y a 2 min"),
    html.Div(id="analysis-diagnostic", className="diagnostic-grid"),

    # Ecarts de performance
    section_title("Écarts de performance", meta="3 indicateurs"),
    html.Div(id="analysis-ecarts", className="ecarts-card"),

    # Comparaison scenarios
    section_title("Comparaison de scénarios"),
    chart_card("Performance par stratégie",
                dcc.Graph(id="analysis-chart-scen",
                          config={"displayModeBar": False})),

    # Recommendation
    html.Div(id="analysis-recommendation"),

    # Export
    section_title("Export des résultats"),
    html.Div(style={"display": "grid", "grid-template-columns": "1fr 1fr",
                    "gap": "12px", "margin-bottom": "24px"},
              children=[
        html.Button([icon("download"), "  Télécharger CSV"],
                    id="btn-export-csv", className="btn btn-secondary"),
        html.Button([icon("download"), "  Télécharger JSON"],
                    id="btn-export-json", className="btn btn-secondary"),
    ]),
    dcc.Download(id="download-csv"),
    dcc.Download(id="download-json"),

    footer(),
])


@callback(
    [Output("analysis-diagnostic", "children"),
     Output("analysis-ecarts", "children"),
     Output("analysis-chart-scen", "figure"),
     Output("analysis-recommendation", "children")],
    Input("config-store", "data"),
)
def update_analysis(store):
    if not store:
        store = {}

    try:
        resultat = simuler_scenario(store)
    except Exception as e:
        return (None, None, {}, alert("danger", "Erreur", f"{e}", "alert"))

    kpis_data = resultat['KPIs']
    securite = resultat['securite']

    v_actuel = store.get('v_f', 15.0)
    prod_actuel = kpis_data['Z1_production_t_jour']
    sec_actuel = kpis_data['Z2_SEC_kWh_tonne']
    age_lub = store.get('age_lubrifiant_jours', 30)
    T_actuel = kpis_data['T_max_C']

    sous_perf = (prod_actuel < REFERENCE['production'] * 0.95
                  or sec_actuel > REFERENCE['consommation'] * 1.05)

    # Cartes diagnostic
    diagnostic = [
        comparison_card(
            "actual", "Conditions actuelles",
            "Sous-performance" if sous_perf else "Conforme",
            "danger" if sous_perf else "success",
            [
                ("Vitesse de ligne", f"{v_actuel:.1f} m/s"),
                ("Production", f"{prod_actuel:.1f} t/jour"),
                ("Consommation énergétique", f"{sec_actuel:.0f} kWh/t"),
                ("Âge lubrifiant", f"{age_lub} jours"),
                ("Température sortie", f"{T_actuel:.1f} °C"),
            ],
        ),
        comparison_card(
            "reference", "Référence constructeur", "Cible", "success",
            [
                ("Vitesse nominale", f"{REFERENCE['vitesse']:.1f} m/s"),
                ("Production nominale", f"{REFERENCE['production']:.1f} t/jour"),
                ("Consommation nominale", f"{REFERENCE['consommation']:.0f} kWh/t"),
                ("Maintenance recommandée", f"{REFERENCE['maintenance']} jours"),
                ("Température cible", f"≤ {REFERENCE['temperature']:.1f} °C"),
            ],
        ),
    ]

    # Ecarts
    ecart_v = (v_actuel - REFERENCE['vitesse']) / REFERENCE['vitesse'] * 100
    ecart_prod = (prod_actuel - REFERENCE['production']) / REFERENCE['production'] * 100
    ecart_sec = (sec_actuel - REFERENCE['consommation']) / REFERENCE['consommation'] * 100

    ecarts = [
        ecart_bar("Vitesse", "m/s", v_actuel, REFERENCE['vitesse'], ecart_v),
        ecart_bar("Production", "t/jour", prod_actuel, REFERENCE['production'], ecart_prod),
        ecart_bar("Consommation", "kWh/t", sec_actuel, REFERENCE['consommation'], ecart_sec),
    ]

    # Comparaison scenarios
    scenarios = {
        "Actuel": {"Z1": prod_actuel, "Z2": sec_actuel},
        "Référence": {"Z1": REFERENCE['production'], "Z2": REFERENCE['consommation']},
    }
    fig_scen = scenarios_comparison(scenarios)

    # Recommandation
    if not sous_perf:
        rec_type = "success"
        rec_titre = "Performance conforme"
        rec_msg = (f"Production {prod_actuel:.1f} t/j et SEC {sec_actuel:.0f} kWh/t "
                    f"alignés avec la référence constructeur.")
    else:
        rec_type = "warning"
        actions = []
        if ecart_prod < -5:
            actions.append("augmenter la vitesse de ligne")
        if ecart_sec > 5:
            actions.append("renouveler le lubrifiant")
        if T_actuel > 110:
            actions.append("renforcer le refroidissement")
        rec_titre = "Actions correctrices recommandées"
        rec_msg = ("Pour atteindre les cibles constructeur, envisager : "
                    + ", ".join(actions) + ". "
                    "Lancez le Module Optimisation pour une recherche systématique.")

    rec = html.Div([
        alert(rec_type, rec_titre, rec_msg,
               icon_name="check" if rec_type == "success" else "alert"),
        recommendation_box(
            "Prochaine étape",
            "Le Module Optimisation explore via NSGA-II l'espace des "
            "configurations possibles et identifie les compromis "
            "production / consommation les plus performants."
        ),
    ])

    return diagnostic, ecarts, fig_scen, rec


# ═══ Export CSV ═══
@callback(
    Output("download-csv", "data"),
    Input("btn-export-csv", "n_clicks"),
    [dash.dependencies.State("config-store", "data")],
    prevent_initial_call=True,
)
def export_csv(n_clicks, store):
    if not n_clicks:
        return None
    if not store:
        store = {}
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
            f"{resultat['puissances'][i]/1000:.3f},{resultat['delta_T'][i]:.2f},"
            f"{resultat['temperatures'][i+1]:.2f},{resultat['mu_par_passe'][i]:.5f}"
        )
    return dict(content="\n".join(lines), filename="sad_analyse.csv")


# ═══ Export JSON ═══
@callback(
    Output("download-json", "data"),
    Input("btn-export-json", "n_clicks"),
    [dash.dependencies.State("config-store", "data")],
    prevent_initial_call=True,
)
def export_json(n_clicks, store):
    if not n_clicks:
        return None
    if not store:
        store = {}
    try:
        resultat = simuler_scenario(store)
    except Exception:
        return None

    import json
    payload = {
        "configuration": store,
        "KPIs": resultat['KPIs'],
        "securite": {
            "C1_mecanique_ok": resultat['securite']['C1_mecanique']['ok'],
            "C2_thermique_ok": resultat['securite']['C2_thermique']['securite_ok'],
            "C3_moteur_ok": resultat['securite']['C3_moteur']['ok'],
            "C4_tribologique_ok": resultat['securite']['C4_tribologique']['ok'],
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
    }
    return dict(content=json.dumps(payload, indent=2),
                 filename="sad_analyse.json")
