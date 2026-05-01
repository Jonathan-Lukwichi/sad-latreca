"""
Composants reutilisables : KPI cards, Module cards, Feature cards, Alerts.
"""

from dash import html
from components.icons import icon


# ═══════════════════════════════════════════════════════════════
# KPI CARD
# ═══════════════════════════════════════════════════════════════

def kpi_card(icon_name, label, value, unit=None, trend=None,
             trend_type="up", footer=None, dark=False, sparkline=None):
    """
    Carte KPI premium avec icone, trend pill et sparkline optionnel.

    Parameters
    ----------
    icon_name : str
        Nom de l'icone (factory, settings, chip, drop, ...)
    label : str
        Libelle (ex: "Production")
    value : str
        Valeur principale (ex: "26.4")
    unit : str, optional
        Unite affichee en petit (ex: "t/j")
    trend : str, optional
        Texte du badge tendance (ex: "+12%")
    trend_type : str
        "up" / "down" / "flat" / "warning"
    footer : str, optional
        Texte sous la valeur (ex: "Optimise")
    dark : bool
        True pour la variante sombre vert nuit
    sparkline : dcc.Graph, optional
        Mini-graphique a afficher
    """
    css_class = "kpi-card dark" if dark else "kpi-card"

    trend_html = None
    if trend:
        trend_arrow_name = ("trend-up" if trend_type == "up"
                            else "trend-down" if trend_type == "down"
                            else None)
        children = []
        if trend_arrow_name:
            children.append(icon(trend_arrow_name))
        children.append(html.Span(trend))
        trend_html = html.Span(
            className=f"kpi-trend {trend_type}",
            children=children,
        )

    value_children = [html.Span(value, className="kpi-value-num")]
    if unit:
        value_children.append(html.Span(unit, className="kpi-unit"))

    foot_html = None
    if footer:
        foot_html = html.Div(
            className="kpi-foot",
            children=[icon("check"), html.Span(footer)],
        )

    spark_html = None
    if sparkline is not None:
        spark_html = html.Div(className="kpi-spark", children=sparkline)

    return html.Div(
        className=css_class,
        children=[
            html.Div(
                className="kpi-head",
                children=[
                    html.Div(className="kpi-icon", children=icon(icon_name)),
                    trend_html,
                ],
            ),
            html.Div(label, className="kpi-label"),
            html.Div(className="kpi-value", children=value_children),
            foot_html,
            spark_html,
        ],
    )


# ═══════════════════════════════════════════════════════════════
# MODULE CARD
# ═══════════════════════════════════════════════════════════════

def module_card(icon_name, title, subtitle, description):
    """Carte module pour la page d'accueil."""
    return html.Div(
        className="module-card",
        children=[
            html.Div(
                className="module-card-header",
                children=[
                    html.Div(className="module-icon", children=icon(icon_name)),
                    html.Div([
                        html.Div(title, className="module-title"),
                        html.Div(subtitle, className="module-subtitle"),
                    ]),
                ],
            ),
            html.Div(description, className="module-description"),
        ],
    )


# ═══════════════════════════════════════════════════════════════
# FEATURE CARD
# ═══════════════════════════════════════════════════════════════

def feature_card(icon_name, title, description):
    """Carte fonctionnalite (3 colonnes)."""
    return html.Div(
        className="feature-card",
        children=[
            html.Div(className="feature-icon-wrap", children=icon(icon_name)),
            html.Div(title, className="feature-title"),
            html.Div(description, className="feature-text"),
        ],
    )


# ═══════════════════════════════════════════════════════════════
# SECTION TITLE
# ═══════════════════════════════════════════════════════════════

def section_title(title, meta=None):
    """Titre de section avec accent dore."""
    children = [
        html.Span(className="accent"),
        html.H3(title),
    ]
    if meta:
        children.append(html.Span(meta, className="meta"))
    return html.Div(className="sec-title", children=children)


# ═══════════════════════════════════════════════════════════════
# PAGE HEADER
# ═══════════════════════════════════════════════════════════════

def page_header(icon_name, title, subtitle, badge="MODULE", pill=None,
                pill_type="success"):
    """
    Header de page consistent.

    Parameters
    ----------
    pill : str, optional
        Pill contextuelle a cote du badge (ex: "Validé", "Cuivre ETP")
    pill_type : str
        "success" / "warning" / "danger" / "info" / "neutral"
    """
    right_children = []
    if pill:
        right_children.append(
            html.Span(pill, className=f"page-header-pill pill-{pill_type}")
        )
    right_children.append(html.Div(badge, className="page-header-badge"))

    return html.Div(
        className="page-header",
        children=[
            html.Div(
                className="page-header-left",
                children=[
                    html.Div(className="page-header-icon", children=icon(icon_name)),
                    html.Div(
                        className="page-header-text",
                        children=[
                            html.H1(title),
                            html.P(subtitle),
                        ],
                    ),
                ],
            ),
            html.Div(className="page-header-right", children=right_children),
        ],
    )


# ═══════════════════════════════════════════════════════════════
# ALERT
# ═══════════════════════════════════════════════════════════════

def alert(type_alert, title, content, icon_name="info"):
    """Alerte stylisee : success / warning / danger / info."""
    return html.Div(
        className=f"alert alert-{type_alert}",
        children=[
            icon(icon_name),
            html.Div([
                html.Strong(title),
                html.Div(content, className="alert-text"),
            ]),
        ],
    )


# ═══════════════════════════════════════════════════════════════
# RECOMMENDATION BOX
# ═══════════════════════════════════════════════════════════════

def recommendation_box(title, content):
    """Boite de recommandation doree."""
    return html.Div(
        className="recommendation-box",
        children=[
            html.Div(
                className="recommendation-title",
                children=[icon("lightbulb"), html.Span(f" {title}")],
            ),
            html.Div(content, className="recommendation-content"),
        ],
    )


# ═══════════════════════════════════════════════════════════════
# CHART CARD
# ═══════════════════════════════════════════════════════════════

def chart_card(title, chart, meta=None):
    """Carte contenant un graphique avec titre et meta."""
    title_children = [html.Span(title)]
    if meta:
        title_children.append(html.Span(meta, className="meta"))
    return html.Div(
        className="chart-card",
        children=[
            html.Div(className="chart-card-title", children=title_children),
            chart,
        ],
    )


# ═══════════════════════════════════════════════════════════════
# CONTROL CARD
# ═══════════════════════════════════════════════════════════════

def control_card(children):
    """Carte conteneur pour les controles (sliders, inputs)."""
    return html.Div(className="control-card", children=children)


def control_label(text, value=None):
    """Label pour un controle, avec valeur affichee a droite."""
    children = [html.Span(text)]
    if value is not None:
        children.append(html.Span(value, className="control-value"))
    return html.Label(className="control-label", children=children)


# ═══════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════

def footer():
    """Footer minimal."""
    return html.Div(
        className="footer-section",
        children=[
            html.Span("SAD LATRECA", className="footer-brand"),
            html.Span(" · Plateforme d'optimisation industrielle"),
        ],
    )
