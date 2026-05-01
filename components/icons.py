"""
Icones Bootstrap Icons (font d'icones via CDN, charge dans app.py).

Approche : html.I(className="bi bi-X") — la font est chargee globalement,
chaque icone est rendue par CSS, sans SVG inline ni dangerously_allow_html.
Marche dans tous les navigateurs, pas de probleme de cache, couleur heritee.

Usage :
    icon("home")              # icone par defaut
    icon("zap", "ma-classe")  # avec classes additionnelles
    icon("settings", size=20) # taille forcee en px
"""

from dash import html


# ════════════════════════════════════════════════════════════════
# Mapping noms internes -> classes Bootstrap Icons
# https://icons.getbootstrap.com/
# ════════════════════════════════════════════════════════════════

ICON_MAP = {
    # Navigation / Generic
    "home":         "house",
    "settings":     "gear",
    "menu":         "list",
    "search":       "search",
    "bell":         "bell",
    "help":         "question-circle",
    "info":         "info-circle",
    "refresh":      "arrow-clockwise",

    # Industrie / Process
    "factory":      "building",
    "chip":         "cpu",
    "package":      "box",
    "layers":       "layers",
    "shield":       "shield",
    "target":       "bullseye",

    # Physique / Mesures
    "drop":         "droplet",
    "thermometer":  "thermometer-half",
    "zap":          "lightning-fill",
    "activity":     "activity",

    # Charts / Data
    "chart":        "bar-chart",
    "line-chart":   "graph-up",
    "trend-up":     "graph-up-arrow",
    "trend-down":   "graph-down-arrow",

    # Actions
    "play":         "play-fill",
    "arrow":        "arrow-right",
    "check":        "check-lg",
    "alert":        "exclamation-triangle",
    "lightbulb":    "lightbulb",
    "download":     "download",
    "file":         "file-earmark",
}


def icon(name: str, css_class: str = "", size: int = None):
    """
    Retourne un html.I avec la classe Bootstrap Icons appropriee.

    Parameters
    ----------
    name : str
        Nom interne (cle de ICON_MAP). Si inconnu, utilise 'bar-chart'.
    css_class : str
        Classes CSS additionnelles.
    size : int, optional
        Taille forcee en pixels (sinon herite de font-size du parent).
    """
    bi_name = ICON_MAP.get(name, "bar-chart")
    classes = f"bi bi-{bi_name} icon icon-{name} {css_class}".strip()

    style = {
        "display": "inline-flex",
        "alignItems": "center",
        "justifyContent": "center",
        "lineHeight": 1,
        "verticalAlign": "middle",
    }
    if size is not None:
        style["fontSize"] = f"{size}px"

    return html.I(className=classes, style=style)
