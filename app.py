"""
SAD LATRECA - Application Dash (entree principale)
"""

import dash
from dash import Dash, html, dcc, page_container, Input, Output, State, callback
import dash_bootstrap_components as dbc

from components.sidebar import sidebar


# Valeurs par defaut du Store global
DEFAULT_CONFIG = {
    "K": 335.0, "n": 0.50,
    "d_0": 8.0, "d_f": 2.0, "n_passes": 9,
    "alpha_uniforme": 6.0,
    "alphas": [6.0] * 9,
    "v_f": 15.0, "T_ambient_C": 25.0, "T_shift_h": 8.0, "eta_OEE": 0.75,
    "eta_cooling": 0.6,
    "lubricant_key": "savon_calcique",
    "mu_0": 0.060, "beta": 0.30, "gamma": 1.5e-6, "Q_lub": 65000.0,
    "age_lubrifiant_jours": 30,
}


# ════════════════════════════════════════════════════════════════
# Initialisation de l'application
# ════════════════════════════════════════════════════════════════

app = Dash(
    __name__,
    use_pages=True,                                    # active le routing automatique des pages/
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        # Bootstrap Icons : font d'icones officielle (1500+ icones)
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css",
    ],
    suppress_callback_exceptions=True,
    title="SAD LATRECA",
    update_title=None,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {"name": "google", "content": "notranslate"},
        {"http-equiv": "Content-Language", "content": "fr"},
    ],
)

# Force la langue FR sur la racine HTML pour empecher la traduction automatique
app.index_string = """<!DOCTYPE html>
<html lang="fr" translate="no">
    <head>
        {%metas%}
        <title>{%title%}</title>
        <meta name="google" content="notranslate">
        {%favicon%}
        {%css%}
    </head>
    <body class="notranslate">
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""

# Necessaire pour les deploiements Gunicorn / Render / Railway
server = app.server


# ════════════════════════════════════════════════════════════════
# Layout global (commun a toutes les pages)
# ════════════════════════════════════════════════════════════════

app.layout = html.Div(
    id="app-root",
    className="app",                                   # toggle ajoute "sidebar-collapsed"
    children=[
        # Store global de configuration (persiste entre les pages)
        dcc.Store(id="config-store", storage_type="session", data=DEFAULT_CONFIG),
        # Store global d'optimisation NSGA-II (lu par Accueil + Analyse globale)
        dcc.Store(id="opt-global-store", storage_type="session", data=None),
        # Marqueur "config touchee par l'utilisateur" (pour l'etat 'Mode demo')
        dcc.Store(id="config-touched", storage_type="session", data=False),
        # Marqueur de la derniere analyse (timestamp ISO)
        dcc.Store(id="last-analysis-store", storage_type="session", data=None),
        # Trigger de redirection apres reset (rempli par la callback de reset)
        dcc.Location(id="app-redirect", refresh=False),
        # Etat sidebar (open/collapsed) - persiste entre rafraichissements
        dcc.Store(id="sidebar-state", storage_type="session", data={"open": True}),
        sidebar(),
        # Overlay sombre cliquable (visible uniquement en mode mobile quand sidebar ouverte)
        html.Div(id="sidebar-overlay", className="sidebar-overlay", n_clicks=0),
        html.Main(
            className="main-content",
            children=[
                page_container,                        # injecte la page active selon l'URL
            ],
        ),
    ],
)


# ════════════════════════════════════════════════════════════════
# Callback : toggle de la sidebar (bouton hamburger + overlay mobile)
# ════════════════════════════════════════════════════════════════

@callback(
    [Output("app-root", "className"),
     Output("sidebar-state", "data")],
    [Input("btn-sidebar-toggle", "n_clicks"),
     Input("sidebar-overlay", "n_clicks")],
    State("sidebar-state", "data"),
    prevent_initial_call=True,
)
def toggle_sidebar(n_burger, n_overlay, state):
    """
    Bascule l'etat ouvert/ferme de la sidebar.
    - Click sur hamburger : toggle
    - Click sur overlay mobile : ferme toujours
    """
    state = state or {"open": True}
    is_open = bool(state.get("open", True))

    # Detection du declencheur
    triggered = (dash.callback_context.triggered[0]["prop_id"]
                 if dash.callback_context.triggered else "")

    if triggered.startswith("sidebar-overlay"):
        new_open = False
    else:
        new_open = not is_open

    cls = "app" if new_open else "app sidebar-collapsed"
    return cls, {"open": new_open}


# ════════════════════════════════════════════════════════════════
# Callback : reinitialiser l'analyse (HARD RESET)
# ════════════════════════════════════════════════════════════════
# Vide tous les stores (config remise aux defauts, optim videe, marqueurs RAZ)
# puis redirige vers /config pour forcer une nouvelle saisie.
# ────────────────────────────────────────────────────────────────

@callback(
    [Output("config-store", "data", allow_duplicate=True),
     Output("opt-global-store", "data", allow_duplicate=True),
     Output("config-touched", "data", allow_duplicate=True),
     Output("last-analysis-store", "data", allow_duplicate=True),
     Output("app-redirect", "pathname")],
    Input("btn-reset-analysis", "n_clicks"),
    prevent_initial_call=True,
)
def reset_analysis(n_clicks):
    """Hard reset : vide tous les stores et redirige vers /config."""
    if not n_clicks:
        return (dash.no_update,) * 5
    return DEFAULT_CONFIG.copy(), None, False, None, "/config"


# ════════════════════════════════════════════════════════════════
# Callback : marquer la config comme "touchee" des qu'un slider bouge
# ════════════════════════════════════════════════════════════════

@callback(
    Output("config-touched", "data", allow_duplicate=True),
    Input("config-store", "data"),
    State("config-touched", "data"),
    prevent_initial_call=True,
)
def mark_config_touched(config, already_touched):
    """Bascule a True des le premier changement reel."""
    if already_touched:
        return dash.no_update
    if not config:
        return dash.no_update
    # Comparer la config courante au DEFAULT_CONFIG
    for k, v in DEFAULT_CONFIG.items():
        if config.get(k) != v:
            return True
    return dash.no_update


# ════════════════════════════════════════════════════════════════
# Lancement
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True, port=8050, host="0.0.0.0")
