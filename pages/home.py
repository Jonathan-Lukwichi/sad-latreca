"""Page 01 - Accueil (KPIs dynamiques + bouton de reinitialisation)"""

import dash
from dash import html, dcc, Input, Output, callback

from components.cards import (
    kpi_card, module_card, feature_card, section_title, footer
)
from components.icons import icon
from components.topbar import topbar as _topbar


dash.register_page(__name__, path="/", name="Accueil", order=1)


def topbar():
    return _topbar(["SAD LATRECA", "Accueil"])


# ════════════════════════════════════════════════════════════════
# Hero (statique : titre + actions ; meta dynamique via callback)
# ════════════════════════════════════════════════════════════════

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
                        "Plateforme intelligente d'optimisation et de "
                        "maintenance prédictive pour les lignes de tréfilage "
                        "industriel. Diagnostic, simulation multi-physique et "
                        "recommandations en quelques clics."
                    ),
                    html.Div(
                        className="hero-actions",
                        children=[
                            dcc.Link(
                                html.Button(
                                    [icon("play"),
                                     "  Démarrer une analyse  ",
                                     icon("arrow")],
                                    className="btn btn-gold btn-large",
                                ),
                                href="/config",
                            ),
                            html.Button(
                                [icon("refresh"),
                                 "  Réinitialiser l'analyse"],
                                id="btn-reset-analysis",
                                n_clicks=0,
                                className="btn btn-ghost btn-large",
                                title=("Vide la configuration et les résultats "
                                       "d'optimisation puis revient à la "
                                       "saisie."),
                            ),
                        ],
                    ),
                ],
            ),
            # Meta (dynamique - rempli par callback)
            html.Div(id="hero-meta", className="hero-meta"),
        ],
    )


# ════════════════════════════════════════════════════════════════
# KPIs (entierement dynamiques)
# ════════════════════════════════════════════════════════════════

def kpis_container():
    return html.Section(id="home-kpis", className="kpi-grid")


# ════════════════════════════════════════════════════════════════
# Sections statiques (features + modules)
# ════════════════════════════════════════════════════════════════

def features():
    return html.Section(children=[
        section_title("Fonctionnalités principales", meta="03 capacités clés"),
        html.Div(className="feature-grid", children=[
            feature_card("search", "Diagnostic Avancé",
                          "Identifiez en quelques minutes les écarts par "
                          "rapport aux références constructeur et leur "
                          "impact sur la production."),
            feature_card("activity", "Simulation Multi-Modules",
                          "Modélisez le comportement de votre ligne avec 5 "
                          "modules scientifiques couplés en temps réel."),
            feature_card("target", "Optimisation Automatique",
                          "Trouvez les configurations qui maximisent la "
                          "production tout en minimisant la consommation "
                          "d'énergie."),
        ]),
    ])


def modules():
    return html.Section(children=[
        section_title("Modules disponibles", meta="06 modules couplés"),
        html.Div(className="module-grid", children=[
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
        ]),
    ])


# ════════════════════════════════════════════════════════════════
# Layout
# ════════════════════════════════════════════════════════════════

layout = html.Div([
    topbar(),
    hero(),
    kpis_container(),
    features(),
    modules(),
    footer(),
])


# ════════════════════════════════════════════════════════════════
# Callbacks : remplissage dynamique du hero meta + des KPIs
# ════════════════════════════════════════════════════════════════

def _hero_meta_item(label, value, dot=False):
    """Construit un bloc meta du hero."""
    children = []
    if dot:
        children.append(html.Span(className="meta-dot"))
    children.append(value)
    return html.Div(
        className="hero-meta-item",
        children=[
            html.Div(label, className="meta-label"),
            html.Div(className="meta-value", children=children),
        ],
    )


def _format_relative_time(iso_ts):
    """Formate un timestamp ISO en relatif (ex: 'il y a 5 min')."""
    if not iso_ts:
        return "Aucune"
    try:
        from datetime import datetime
        ts = datetime.fromisoformat(iso_ts)
        delta = datetime.now() - ts
        sec = int(delta.total_seconds())
        if sec < 60:
            return f"il y a {sec} s"
        if sec < 3600:
            return f"il y a {sec // 60} min"
        if sec < 86400:
            return f"il y a {sec // 3600} h"
        return f"il y a {sec // 86400} j"
    except Exception:
        return "—"


@callback(
    Output("hero-meta", "children"),
    [Input("config-touched", "data"),
     Input("opt-global-store", "data"),
     Input("last-analysis-store", "data")],
)
def update_hero_meta(touched, opt_store, last_ts):
    """Hero meta dynamique : reflete l'etat reel du systeme."""
    if not touched:
        etat_label = "État système"
        etat_value = "Mode démo"
    elif opt_store and opt_store.get('compromis'):
        etat_label = "État système"
        etat_value = "Optimisé"
    else:
        etat_label = "État système"
        etat_value = "Configuré"

    n_sol = (opt_store or {}).get('n_solutions', 0)
    if n_sol > 0:
        modules_label = "Solutions Pareto"
        modules_value = f"{n_sol} disponibles"
    else:
        modules_label = "Modules couplés"
        modules_value = "5 physiques actifs"

    return [
        _hero_meta_item(etat_label, etat_value, dot=True),
        _hero_meta_item("Dernière analyse",
                         _format_relative_time(last_ts)),
        _hero_meta_item(modules_label, modules_value),
    ]


@callback(
    Output("home-kpis", "children"),
    [Input("config-touched", "data"),
     Input("config-store", "data"),
     Input("opt-global-store", "data"),
     Input("last-analysis-store", "data")],
)
def update_kpis(touched, config, opt_store, last_ts):
    """KPIs dynamiques bases sur l'etat reel."""
    config = config or {}
    opt_store = opt_store or {}

    # KPI 1 : Configuration
    if not touched:
        cfg_value = "Démo"
        cfg_unit = None
        cfg_trend = "valeurs par défaut"
        cfg_trend_type = "warning"
        cfg_footer = "Cliquez 'Démarrer une analyse'"
    else:
        n_set = sum(1 for v in config.values()
                     if v is not None and v != "")
        cfg_value = f"{n_set}"
        cfg_unit = "params"
        cfg_trend = "personnalisée"
        cfg_trend_type = "up"
        cfg_footer = "Configuration validée"

    # KPI 2 : Optimisation NSGA-II
    n_sol = opt_store.get('n_solutions', 0)
    if n_sol > 0:
        opt_value = f"{n_sol}"
        opt_unit = "Pareto"
        opt_trend = f"{opt_store.get('n_evaluations', 0)} évaluations"
        opt_trend_type = "up"
        opt_footer = (f"Calcul en {opt_store.get('temps', 0):.1f} s")
    else:
        opt_value = "—"
        opt_unit = None
        opt_trend = "non lancée"
        opt_trend_type = "flat"
        opt_footer = "Lancez NSGA-II depuis Optimisation"

    # KPI 3 : Lubrifiant configure
    lub_key = config.get('lubricant_key')
    if lub_key and touched:
        lub_value = lub_key.replace("_", " ").title()
        lub_unit = None
        lub_trend = f"μ₀ = {config.get('mu_0', 0):.3f}"
        lub_trend_type = "flat"
        lub_footer = f"Âge {int(config.get('age_lubrifiant_jours', 0))} j"
    else:
        lub_value = "—"
        lub_unit = None
        lub_trend = "non choisi"
        lub_trend_type = "warning"
        lub_footer = "Choisissez dans Configuration"

    # KPI 4 : Derniere analyse (timestamp)
    rel_time = _format_relative_time(last_ts)
    if last_ts:
        last_value = "✓"
        last_unit = None
        last_trend = rel_time
        last_trend_type = "up"
        last_footer = "Optimisation effectuée"
    else:
        last_value = "—"
        last_unit = None
        last_trend = "Jamais"
        last_trend_type = "flat"
        last_footer = "Aucune analyse en cours"

    return [
        kpi_card(icon_name="settings", label="Configuration",
                 value=cfg_value, unit=cfg_unit,
                 trend=cfg_trend, trend_type=cfg_trend_type,
                 footer=cfg_footer),
        kpi_card(icon_name="target", label="Solutions Pareto",
                 value=opt_value, unit=opt_unit,
                 trend=opt_trend, trend_type=opt_trend_type,
                 footer=opt_footer, dark=True),
        kpi_card(icon_name="drop", label="Lubrifiant actif",
                 value=lub_value, unit=lub_unit,
                 trend=lub_trend, trend_type=lub_trend_type,
                 footer=lub_footer),
        kpi_card(icon_name="chart", label="Dernière analyse",
                 value=last_value, unit=last_unit,
                 trend=last_trend, trend_type=last_trend_type,
                 footer=last_footer),
    ]
