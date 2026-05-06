"""
Topbar minimaliste : hamburger + breadcrumb uniquement.
"""

from dash import html
from components.icons import icon


def topbar(crumbs):
    """
    Genere un topbar coherent pour toutes les pages.

    Parameters
    ----------
    crumbs : list of str
        Fil d'Ariane, ex: ["SAD LATRECA", "Modules", "Matériau"]
    """
    crumb_children = []
    last = len(crumbs) - 1
    for i, c in enumerate(crumbs):
        if i == last:
            crumb_children.append(html.Span(c, className="crumb-current"))
        else:
            crumb_children.append(html.Span(c, className="crumb-step"))
            crumb_children.append(html.Span("/", className="crumb-sep"))

    return html.Div(
        className="topbar",
        children=html.Div(
            className="topbar-inner",
            children=[
                html.Div(
                    className="topbar-left",
                    children=[
                        html.Button(
                            id="btn-sidebar-toggle",
                            n_clicks=0,
                            className="topbar-burger",
                            children=icon("menu"),
                            title="Afficher / masquer la barre latérale",
                            **{"aria-label": "Toggle sidebar"},
                        ),
                        html.Div(className="breadcrumb",
                                  children=crumb_children),
                    ],
                ),
            ],
        ),
    )
