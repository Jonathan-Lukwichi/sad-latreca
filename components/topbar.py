"""
Topbar enrichi : hamburger + breadcrumb + recherche + aide + cloche.
"""

from dash import html, dcc
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
                # Gauche : hamburger (bouton actif) + breadcrumb
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
                        html.Div(className="breadcrumb", children=crumb_children),
                    ],
                ),
                # Droite : recherche + aide + cloche
                html.Div(
                    className="topbar-right",
                    children=[
                        html.Div(
                            className="topbar-search",
                            children=[
                                html.Span(className="search-ic", children=icon("search")),
                                dcc.Input(
                                    type="text",
                                    placeholder="Rechercher un module, un paramètre...",
                                    className="search-input",
                                ),
                            ],
                        ),
                        html.Span(
                            className="topbar-icon-btn",
                            children=icon("help"),
                            title="Aide",
                        ),
                        html.Span(
                            className="topbar-icon-btn",
                            children=[icon("bell"), html.Span(className="bell-dot")],
                            title="Notifications",
                        ),
                    ],
                ),
            ],
        ),
    )
