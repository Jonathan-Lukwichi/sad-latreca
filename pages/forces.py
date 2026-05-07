"""Page 04 - Module Forces (avec boutons Lancer / Initialiser)"""

import dash
from dash import html, dcc, Input, Output, State, callback, dash_table

from components.cards import (
    page_header, section_title, footer, kpi_card,
    chart_card, recommendation_box, alert,
    model_runner_bar, empty_module_placeholder,
)
from components.charts import force_decomposition, forces_per_stage, COLORS
from components.topbar import topbar
from core.coupled_solver import simuler_scenario
from core.avitzur import calculer_force_avitzur


dash.register_page(__name__, path="/forces", name="Module Forces", order=4)


LABEL_RUN = "Lancer les forces"


layout = html.Div([
    topbar(["SAD LATRECA", "Modules", "Forces"]),

    page_header("zap", "Module Forces",
                "Charges mécaniques sur le fil et les outillages",
                badge="MODULE", pill="Zone de sécurité"),

    model_runner_bar(
        LABEL_RUN,
        btn_run_id="btn-run-forces",
        btn_init_id="btn-init-forces",
        info="Calcule les forces de traction et la puissance par passe "
              "via le modèle d'Avitzur (déformation + frottement + interne).",
    ),

    html.Div(id="forces-content",
              children=empty_module_placeholder(LABEL_RUN)),

    footer(),
])


@callback(
    Output("forces-content", "children"),
    [Input("btn-run-forces", "n_clicks"),
     Input("btn-init-forces", "n_clicks")],
    State("config-store", "data"),
    prevent_initial_call=True,
)
def update_forces(n_run, n_init, store):
    """Lance le calcul Forces OU initialise."""
    triggered = (dash.callback_context.triggered[0]["prop_id"]
                 if dash.callback_context.triggered else "")

    if triggered.startswith("btn-init-forces"):
        return empty_module_placeholder(LABEL_RUN)

    store = store or {}

    try:
        resultat = simuler_scenario(store)
    except Exception as e:
        return alert("danger", "Erreur de calcul",
                      f"Impossible de simuler : {e}", "alert")

    n_passes = len(resultat['forces'])
    kpis_data = resultat['KPIs']

    # Recalcul composantes Avitzur par passe
    forces_def, forces_frot, forces_red = [], [], []
    for i in range(n_passes):
        r = calculer_force_avitzur(
            resultat['contraintes_moyennes'][i],
            resultat['diametres'][i], resultat['diametres'][i + 1],
            resultat['mu_par_passe'][i],
            store.get('alphas', [6.0] * n_passes)[i]
        )
        forces_def.append(r['F_deformation'])
        forces_frot.append(r['F_frottement'])
        forces_red.append(r['F_redondant'])

    # KPIs
    kpis = [
        kpi_card("zap", "Force max",
                  f"{max(resultat['forces']):.0f}", unit=" N",
                  trend="critique", trend_type="warning",
                  footer="Charge maximale ligne"),
        kpi_card("activity", "Puissance totale",
                  f"{sum(resultat['puissances']) / 1000:.1f}", unit=" kW",
                  trend="consommée", trend_type="up",
                  footer="Puissance électrique",
                  dark=True),
        kpi_card("shield", "Marge sécurité",
                  f"{kpis_data['marge_mecanique_pourcent']:.0f}", unit="%",
                  trend=("OK" if kpis_data['marge_mecanique_pourcent'] > 30
                          else "ALERTE"),
                  trend_type=("up"
                                if kpis_data['marge_mecanique_pourcent'] > 30
                                else "down"),
                  footer="Avant rupture"),
        kpi_card("chart", "Force cumulée",
                  f"{sum(resultat['forces']):.0f}", unit=" N",
                  trend="totale", trend_type="flat",
                  footer="Sur toutes les étapes"),
    ]

    fig = forces_per_stage(resultat['forces'])

    F_max = max(resultat['forces'])
    F_pic_idx = resultat['forces'].index(F_max) + 1
    lecture = html.Div(className="lecture-box", children=[
        html.Strong("Lecture : "),
        html.Span(
            "la force décroît passe après passe car le diamètre — donc la "
            "section soumise — diminue, malgré l'augmentation de σ. "
            "Le pic de "
        ),
        html.Strong(f"{F_max:,.0f} N".replace(",", " "),
                     style={"color": COLORS['gold-deep']}),
        html.Span(f" se produit à la passe {F_pic_idx}."),
    ])

    table_data = []
    for i in range(n_passes):
        table_data.append({
            "Étape": i + 1,
            "D entrée (mm)": f"{resultat['diametres'][i]:.2f}",
            "D sortie (mm)": f"{resultat['diametres'][i+1]:.2f}",
            "F déf. (N)": f"{forces_def[i]:.0f}",
            "F frot. (N)": f"{forces_frot[i]:.0f}",
            "F int. (N)": f"{forces_red[i]:.0f}",
            "F totale (N)": f"{resultat['forces'][i]:.0f}",
            "P (kW)": f"{resultat['puissances'][i] / 1000:.1f}",
        })

    table = dash_table.DataTable(
        data=table_data,
        columns=[{"name": k, "id": k} for k in table_data[0].keys()],
        style_cell={"textAlign": "center", "fontFamily": "Inter",
                    "fontSize": "12px", "padding": "8px",
                    "border": "1px solid #E5DFCE"},
        style_header={"backgroundColor": "#0A2A1F", "color": "#F2D89A",
                      "fontFamily": "JetBrains Mono", "fontSize": "10px",
                      "fontWeight": "600", "textTransform": "uppercase",
                      "letterSpacing": "0.08em"},
        style_data_conditional=[{"if": {"row_index": "odd"},
                                  "backgroundColor": "#FAFAF7"}],
        style_table={"borderRadius": "14px", "overflow": "hidden"},
    )

    securite = resultat['securite']['C1_mecanique']
    if securite['ok']:
        status = alert("success", "Aucun risque détecté",
                        "Toutes les étapes fonctionnent en zone de "
                        "sécurité mécanique.", icon_name="check")
    else:
        status = alert("danger", "Alerte de sécurité",
                        "Risque de rupture sur certaines étapes. "
                        "Réduisez la cadence.", icon_name="alert")

    rec = recommendation_box(
        "Configuration recommandée",
        f"Force max : {max(resultat['forces']):.0f} N · "
        f"Puissance : {sum(resultat['puissances']) / 1000:.1f} kW · "
        f"Marge : {kpis_data['marge_mecanique_pourcent']:.0f}%. "
        f"Vous pouvez explorer des configurations plus performantes via "
        f"le Module Optimisation."
    )

    return html.Div([
        html.Div(className="kpi-grid", children=kpis),
        section_title("Force d'étirage par passe", meta="Modèle Avitzur"),
        chart_card("Force par étape",
                    dcc.Graph(figure=fig,
                              config={"displayModeBar": False})),
        lecture,
        section_title("Détail par étape"),
        table,
        status,
        rec,
    ])
