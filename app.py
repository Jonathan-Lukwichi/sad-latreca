"""
SAD LATRECA - Application Dash (entree principale)
"""

import dash
from dash import Dash, html, dcc, page_container
import dash_bootstrap_components as dbc

from components.sidebar import sidebar


# Valeurs par defaut du Store global
DEFAULT_CONFIG = {
    "K": 335.0, "n": 0.50,
    "d_0": 8.0, "d_f": 2.0, "n_passes": 9,
    "alpha_uniforme": 6.0,
    "alphas": [6.0] * 9,
    "v_f": 15.0, "T_ambient_C": 25.0, "T_shift_h": 8.0, "eta_OEE": 0.75,
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
    className="app",
    children=[
        # Store global de configuration (persiste entre les pages)
        dcc.Store(id="config-store", storage_type="session", data=DEFAULT_CONFIG),
        sidebar(),
        html.Main(
            className="main-content",
            children=[
                page_container,                        # injecte la page active selon l'URL
            ],
        ),
    ],
)


# ════════════════════════════════════════════════════════════════
# Lancement
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True, port=8050, host="0.0.0.0")
