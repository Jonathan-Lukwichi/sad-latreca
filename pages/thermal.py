"""Page 05 - Module Thermique"""

import dash
from dash import html, dcc, Input, Output, callback, dash_table

from components.cards import (
    page_header, section_title, footer, kpi_card,
    chart_card, recommendation_box, alert,
)
from components.charts import temperature_profile, delta_t_per_stage
from components.topbar import topbar
from core.coupled_solver import simuler_scenario


dash.register_page(__name__, path="/thermal", name="Module Thermique", order=5)


layout = html.Div([
    topbar(["SAD LATRECA", "Modules", "Thermique"]),

    page_header("thermometer", "Module Thermique",
                "Surveillance et prédiction de l'élévation de température · seuil 140°C",
                badge="MODULE · LIVE", pill="Surveillance active"),

    html.Div(id="thermal-kpis", className="kpi-grid"),

    section_title("Visualisations thermiques", meta="02 graphiques"),
    html.Div(className="chart-grid-2", children=[
        chart_card("Profil de température cumulée",
                   dcc.Graph(id="thermal-chart-profile",
                             config={"displayModeBar": False})),
        chart_card("Échauffement par étape (ΔT)",
                   dcc.Graph(id="thermal-chart-delta",
                             config={"displayModeBar": False})),
    ]),

    html.Div(id="thermal-status"),

    section_title("Détail par étape"),
    html.Div(id="thermal-table"),

    html.Div(id="thermal-recommendation"),

    footer(),
])


@callback(
    [Output("thermal-kpis", "children"),
     Output("thermal-chart-profile", "figure"),
     Output("thermal-chart-delta", "figure"),
     Output("thermal-table", "children"),
     Output("thermal-status", "children"),
     Output("thermal-recommendation", "children")],
    Input("config-store", "data"),
)
def update_thermal(store):
    if not store:
        store = {}

    try:
        resultat = simuler_scenario(store)

        # Extraction sécurisée des données
        T_max = float(resultat['KPIs']['T_max_C'])
        marge = float(resultat['KPIs']['marge_thermique_C'])
        sec = resultat['securite']['C2_thermique']
        delta_T_list = [float(x) for x in resultat['delta_T']]
        delta_T_max = max(delta_T_list) if delta_T_list else 0.0

        # KPIs
        if sec['niveau_risque'] == 'OK':
            risque_trend = "OK"
            risque_type = "up"
        elif sec['niveau_risque'] == 'Attention':
            risque_trend = "vigilance"
            risque_type = "warning"
        else:
            risque_trend = "critique"
            risque_type = "down"

        kpis = [
            kpi_card("thermometer", "Température max",
                     f"{T_max:.0f}", unit="°C",
                     trend="ligne complète", trend_type="flat",
                     footer="Atteinte sur la ligne"),
            kpi_card("shield", "Marge thermique",
                     f"{marge:.0f}", unit="°C",
                     trend="OK" if marge > 30 else "FAIBLE",
                     trend_type="up" if marge > 30 else "down",
                     footer="Avant seuil 140°C",
                     dark=True),
            kpi_card("alert", "Niveau risque",
                     sec['niveau_risque'],
                     trend=risque_trend, trend_type=risque_type,
                     footer="État global"),
            kpi_card("zap", "ΔT max par étape",
                     f"{delta_T_max:.1f}", unit="°C",
                     trend="échauffement", trend_type="warning",
                     footer="Pic d'échauffement"),
        ]

        # Graphs
        fig_profile = temperature_profile(resultat['temperatures'], T_seuil=140.0)
        fig_delta = delta_t_per_stage(resultat['delta_T'])

        # Table
        n_passes = len(delta_T_list)
        table_data = []
        for i in range(n_passes):
            table_data.append({
                "Étape": i + 1,
                "D sortie (mm)": f"{resultat['diametres'][i+1]:.2f}",
                "Vitesse (m/s)": f"{resultat['vitesses'][i]:.2f}",
                "ΔT (°C)": f"{delta_T_list[i]:.2f}",
                "T cumulée (°C)": f"{resultat['temperatures'][i+1]:.1f}",
            })

        if table_data:
            columns = [{"name": k, "id": k} for k in table_data[0].keys()]
        else:
            columns = []

        table = dash_table.DataTable(
            data=table_data,
            columns=columns,
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

        # Status
        if T_max > 140:
            status = alert("danger", f"Alerte critique ({T_max:.0f}°C)",
                           "Risques : dégradation du lubrifiant, perte de qualité, "
                           "usure accélérée. Réduisez immédiatement la cadence.",
                           icon_name="alert")
        elif T_max > 110:
            status = alert("warning", f"Vigilance recommandée ({T_max:.0f}°C)",
                           "Proche du seuil critique de 140°C. Surveillez en continu.",
                           icon_name="alert")
        else:
            status = alert("success", f"Fonctionnement nominal ({T_max:.0f}°C)",
                           "Bien en dessous du seuil critique. Marge confortable.",
                           icon_name="check")

        # Recommandation
        if marge > 30:
            action = "Maintenez les conditions actuelles."
        elif marge > 0:
            action = "Réduisez la vitesse ou améliorez la lubrification."
        else:
            action = "Action urgente : réduisez immédiatement la cadence."

        rec = recommendation_box(
            "Action recommandée",
            f"T max : {T_max:.0f}°C · Marge sécurité : {marge:.0f}°C. {action}"
        )

        return kpis, fig_profile, fig_delta, table, status, rec

    except Exception as e:
        # En cas d'erreur n'importe où dans le callback, on affiche une alerte propre
        return (None, {}, {}, None,
                alert("danger", "Erreur de calcul thermique",
                      f"Détail : {str(e)}", icon_name="alert"), None)

