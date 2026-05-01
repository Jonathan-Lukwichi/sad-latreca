"""
Sidebar de navigation gauche - SAD LATRECA
Sections + icones Lucide + badge LIVE + carte utilisateur.
"""

from dash import html, dcc
from components.icons import icon


# Structure : (section, [(path, icone, label, badge_optionnel), ...])
NAV_SECTIONS = [
    ("Navigation", [
        ("/",       "home",     "Accueil",       None),
        ("/config", "settings", "Configuration", None),
    ]),
    ("Modules scientifiques", [
        ("/material",     "layers",      "Matériau",      "LIVE"),
        ("/forces",       "zap",         "Forces",        None),
        ("/thermal",      "thermometer", "Thermique",     None),
        ("/lubrication",  "drop",        "Lubrification", None),
        ("/optimization", "target",      "Optimisation",  None),
    ]),
    ("Diagnostic", [
        ("/analysis", "line-chart", "Analyse globale", None),
    ]),
]


def _nav_item(path, icon_name, label, badge):
    children = [
        html.Span(className="nav-ic", children=icon(icon_name)),
        html.Span(label, className="nav-label"),
    ]
    if badge:
        children.append(html.Span(badge, className="nav-badge"))
    return dcc.Link(
        href=path,
        className="nav-item",
        refresh=False,
        children=children,
    )


def _nav_section(title, items):
    return html.Div(
        className="nav-section",
        children=[
            html.Div(title.upper(), className="nav-section-title"),
            html.Div(
                className="nav-section-items",
                children=[_nav_item(*it) for it in items],
            ),
        ],
    )


def sidebar():
    """Sidebar gauche fixe avec logo + navigation par sections + carte utilisateur."""
    return html.Aside(
        className="sidebar",
        children=[
            # Brand
            html.Div(
                className="sidebar-brand",
                children=[
                    html.Div("SL", className="brand-mark"),
                    html.Div(
                        className="brand-text",
                        children=[
                            html.Div("SAD·LATRECA", className="brand-name"),
                            html.Div("INDUSTRIE 4.0", className="brand-tag"),
                        ],
                    ),
                ],
            ),

            # Navigation par sections
            html.Nav(
                className="sidebar-nav",
                children=[_nav_section(t, items) for t, items in NAV_SECTIONS],
            ),

            # Footer : statut + identite atelier (neutre)
            html.Div(
                className="sidebar-footer",
                children=[
                    html.Div(
                        className="sidebar-status",
                        children=[
                            html.Span(className="status-dot"),
                            html.Span("Système opérationnel"),
                        ],
                    ),
                    html.Div(
                        className="sidebar-user",
                        children=[
                            html.Div(
                                className="user-avatar",
                                children=icon("factory"),
                            ),
                            html.Div(
                                className="user-info",
                                children=[
                                    html.Div("Atelier LATRECA",
                                              className="user-name"),
                                    html.Div("Ligne de tréfilage · 8 passes",
                                              className="user-role"),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
