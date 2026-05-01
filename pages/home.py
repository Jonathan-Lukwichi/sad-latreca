"""Page 01 - Accueil"""

import dash
from dash import html, dcc

from components.cards import (
    kpi_card, module_card, feature_card, section_title, footer
)
from components.charts import sparkline, COLORS
from components.icons import icon
from components.topbar import topbar as _topbar


dash.register_page(__name__, path="/", name="Accueil", order=1)


def topbar():
    return _topbar(["SAD LATRECA", "Accueil"])


# ════ Hero ════
def hero():
    return html.Section(
        className="hero",
        children=[
            html.Div(className="hero-grid"),
            html.Div(
                className="hero-content",
                children=[
                    html.Div(
                        className="hero-tag",
                        children=[
                            html.Span(className="lighten"),
                            "INDUSTRIE 4.0 · TRÉFILAGE INTELLIGENT",
                        ],
                    ),
                    html.H1("Accueil"),
                    html.P(
                        "Plateforme intelligente d'optimisation et de maintenance "
                        "prédictive pour les lignes de tréfilage industriel. "
                        "Diagnostic, simulation multi-physique et recommandations "
                        "en quelques clics."
                    ),
                    html.Div(
                        className="hero-actions",
                        children=[
                            dcc.Link(
                                html.Button(
                                    [icon("play"), "  Démarrer une analyse  ", icon("arrow")],
                                    className="btn btn-gold btn-large",
                                ),
                                href="/config",
                            ),
                            html.Button(
                                "Voir la démo guidée",
                                className="btn btn-ghost btn-large",
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="hero-meta",
                children=[
                    html.Div(
                        className="hero-meta-item",
                        children=[
                            html.Div("État système", className="meta-label"),
                            html.Div(
                                className="meta-value",
                                children=[
                                    html.Span(className="meta-dot"),
                                    "Opérationnel",
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        className="hero-meta-item",
                        children=[
                            html.Div("Dernière synchro", className="meta-label"),
                            html.Div("il y a 2 min", className="meta-value"),
                        ],
                    ),
                    html.Div(
                        className="hero-meta-item",
                        children=[
                            html.Div("Modules couplés", className="meta-label"),
                            html.Div("5 physiques actifs", className="meta-value"),
                        ],
                    ),
                ],
            ),
        ],
    )


# ════ KPIs ════
def kpis():
    return html.Section(
        className="kpi-grid",
        children=[
            kpi_card(
                icon_name="factory",
                label="Lignes surveillées",
                value="9",
                trend="+2 ce mois",
                trend_type="up",
                footer="Couverture totale",
                sparkline=dcc.Graph(
                    figure=sparkline([3, 4, 4, 5, 6, 7, 7, 8, 9], color=COLORS["ink"]),
                    config={"displayModeBar": False},
                ),
            ),
            kpi_card(
                icon_name="chip",
                label="Modules actifs",
                value="6", unit="/6",
                trend="100% sync",
                trend_type="up",
                footer="Tous synchronisés",
                dark=True,
                sparkline=dcc.Graph(
                    figure=sparkline([2, 3, 3, 4, 5, 5, 6, 6, 6], color=COLORS["gold"]),
                    config={"displayModeBar": False},
                ),
            ),
            kpi_card(
                icon_name="drop",
                label="Profils lubrifiants",
                value="4",
                trend="stable",
                trend_type="flat",
                footer="Base à jour",
                sparkline=dcc.Graph(
                    figure=sparkline([4, 4, 4, 4, 4, 4, 4, 4, 4], color=COLORS["blue"]),
                    config={"displayModeBar": False},
                ),
            ),
            kpi_card(
                icon_name="chart",
                label="Analyses effectuées",
                value="42",
                trend="+12 cette semaine",
                trend_type="up",
                footer="Validées par expert",
                sparkline=dcc.Graph(
                    figure=sparkline([8, 12, 14, 18, 22, 28, 30, 38, 42],
                                      color=COLORS["mint-deep"]),
                    config={"displayModeBar": False},
                ),
            ),
        ],
    )


# ════ Features ════
def features():
    return html.Section(
        children=[
            section_title("Fonctionnalités principales", meta="03 capacités clés"),
            html.Div(
                className="feature-grid",
                children=[
                    feature_card(
                        "search",
                        "Diagnostic Avancé",
                        "Identifiez en quelques minutes les écarts par rapport "
                        "aux références constructeur et leur impact sur la production.",
                    ),
                    feature_card(
                        "activity",
                        "Simulation Multi-Modules",
                        "Modélisez le comportement de votre ligne avec 5 modules "
                        "scientifiques couplés en temps réel.",
                    ),
                    feature_card(
                        "target",
                        "Optimisation Automatique",
                        "Trouvez les configurations qui maximisent la production "
                        "tout en minimisant la consommation d'énergie.",
                    ),
                ],
            ),
        ],
    )


# ════ Modules ════
def modules():
    return html.Section(
        children=[
            section_title("Modules disponibles", meta="06 modules couplés"),
            html.Div(
                className="module-grid",
                children=[
                    module_card("chart", "Module Matériau",
                                "Comportement plastique",
                                "Analyse l'évolution de la résistance du matériau "
                                "au fil des étapes successives."),
                    module_card("zap", "Module Forces",
                                "Charges mécaniques",
                                "Évalue les contraintes appliquées sur le fil et "
                                "les outillages en zone de sécurité."),
                    module_card("thermometer", "Module Thermique",
                                "Surveillance température",
                                "Prédit l'élévation de température et alerte en "
                                "cas de dépassement du seuil critique."),
                    module_card("drop", "Module Lubrification",
                                "Suivi vieillissement",
                                "Anticipe le vieillissement du lubrifiant et "
                                "planifie les remplacements optimaux."),
                    module_card("target", "Module Optimisation",
                                "Recherche multi-objectifs",
                                "Identifie automatiquement les configurations "
                                "optimales pour vos objectifs."),
                    module_card("package", "Module Analyse",
                                "Diagnostic & Export",
                                "Compare les scénarios et génère des rapports "
                                "PDF/CSV pour vos équipes."),
                ],
            ),
        ],
    )


# ════ Layout ════
layout = html.Div([
    topbar(),
    hero(),
    kpis(),
    features(),
    modules(),
    footer(),
])
