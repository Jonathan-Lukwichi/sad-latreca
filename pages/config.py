"""Page 02 - Configuration"""

import dash
from dash import html, dcc, Input, Output, State, callback

from components.cards import (
    page_header, section_title, alert, footer,
)
from components.icons import icon
from components.topbar import topbar
from core.parameters import load_lubricants_database


dash.register_page(__name__, path="/config", name="Configuration", order=2)

LUBRICANTS = load_lubricants_database()
LUB_OPTIONS = [
    {"label": v["nom"], "value": k}
    for k, v in LUBRICANTS.items()
    if not k.startswith("_")
]


# ════════════════════════════════════════════════════════════════
# Composants reutilisables
# ════════════════════════════════════════════════════════════════

def preset_card(icon_name, title, subtitle, btn_id):
    """Carte preset cliquable (icone + titre + sous-titre)."""
    return html.Button(
        id=btn_id,
        n_clicks=0,
        className="preset-card",
        children=[
            html.Div(className="preset-icon", children=icon(icon_name)),
            html.Div(
                className="preset-text",
                children=[
                    html.Div(title, className="preset-title"),
                    html.Div(subtitle, className="preset-subtitle"),
                ],
            ),
        ],
    )


def section_card(icon_name, title, subtitle, pill_text=None,
                 pill_type="warning", children=None):
    """
    Carte de section avec en-tete (icone + titre + sous-titre + pill optionnel).
    """
    head_right = (
        html.Span(pill_text, className=f"section-pill section-pill-{pill_type}")
        if pill_text else None
    )
    head = html.Div(
        className="section-card-head",
        children=[
            html.Div(
                className="section-card-title",
                children=[
                    html.Div(className="section-card-ic", children=icon(icon_name)),
                    html.Div(
                        className="section-card-text",
                        children=[
                            html.Span(title, className="sc-title"),
                            html.Span(f" · {subtitle}", className="sc-sub")
                            if subtitle else None,
                        ],
                    ),
                ],
            ),
            head_right,
        ],
    )
    return html.Div(
        className="section-card",
        children=[head, html.Div(className="section-card-body",
                                  children=children or [])],
    )


def slider(id_, min_, max_, value, step, label, unit="", precision=2):
    """Slider stylise avec label + box valeur a droite + min/max sous le rail."""
    if isinstance(value, float):
        if precision == 0:
            display = f"{value:.0f}{unit}"
        else:
            display = f"{value:.{precision}f}{unit}"
    else:
        display = f"{value}{unit}"

    return html.Div(
        className="slider-block",
        children=[
            html.Div(
                className="slider-head",
                children=[
                    html.Span(label, className="slider-label"),
                    html.Span(display,
                              id={"type": "value-display", "id": id_},
                              className="slider-value-box"),
                ],
            ),
            dcc.Slider(
                id=id_,
                min=min_, max=max_, value=value, step=step,
                marks=None, tooltip=None,
                updatemode="drag",
                className="sad-slider",
            ),
            html.Div(
                className="slider-bounds",
                children=[
                    html.Span(f"{min_:g}"),
                    html.Span(f"{max_:g}"),
                ],
            ),
        ],
    )


# ════════════════════════════════════════════════════════════════
# Layout
# ════════════════════════════════════════════════════════════════

layout = html.Div([
    topbar(["SAD LATRECA", "Configuration"]),

    page_header("settings", "Configuration",
                "Paramètres opérationnels de la ligne de tréfilage · 9 passes",
                badge="ÉTAPE 1/3", pill="Validé", pill_type="success"),

    # Preset cards (icon + title + subtitle)
    section_card("zap", "Préréglages rapides", None,
                  pill_text="4 disponibles", pill_type="neutral",
                  children=[
        html.Div(className="preset-grid", children=[
            preset_card("factory", "LATRECA Réel · Avril 2026",
                         "Données collectées en atelier",
                         "btn-preset-latreca"),
            preset_card("info", "Conditions actuelles",
                         "État relevé en atelier",
                         "btn-preset-current"),
            preset_card("check", "Référence constructeur",
                         "Spécifications LATRECA d'origine",
                         "btn-preset-constructor"),
            preset_card("refresh", "Réinitialiser",
                         "Valeurs par défaut",
                         "btn-preset-reset"),
        ]),
    ]),

    # Materiau
    section_card("layers", "Matériau", "Cuivre ETP",
                  pill_text="Loi Hollomon", pill_type="warning",
                  children=[
        html.Div(className="control-row", children=[
            slider("slider-K", 200, 500, 335, 1,
                    "Coefficient de résistance K (MPa)", precision=0),
            slider("slider-n", 0.1, 1.0, 0.50, 0.01,
                    "Indice de durcissement n", precision=2),
        ]),
    ]),

    # Geometrie : pill dynamique avec span interne mis a jour par callback
    html.Div(
        className="section-card",
        children=[
            html.Div(
                className="section-card-head",
                children=[
                    html.Div(
                        className="section-card-title",
                        children=[
                            html.Div(className="section-card-ic",
                                      children=icon("package")),
                            html.Div(
                                className="section-card-text",
                                children=[
                                    html.Span("Géométrie de la ligne",
                                              className="sc-title"),
                                ],
                            ),
                        ],
                    ),
                    html.Span(
                        id="reduction-totale-pill",
                        className="section-pill section-pill-success",
                        children="Réduction totale —",
                    ),
                ],
            ),
            html.Div(className="section-card-body", children=[
                html.Div(className="control-row", children=[
                    slider("slider-d0", 1, 12, 8.0, 0.1,
                            "Diamètre d'entrée (mm)", precision=2),
                    slider("slider-df", 0.5, 6, 2.0, 0.1,
                            "Diamètre de sortie (mm)", precision=2),
                ]),
                html.Div(className="control-row", children=[
                    html.Div([
                        html.Div("Nombre d'étapes (passes)",
                                  className="slider-label",
                                  style={"margin-bottom": "8px"}),
                        html.Div(className="stepper", children=[
                            html.Button("−", id="step-minus", n_clicks=0,
                                          className="stepper-btn"),
                            html.Span(id="step-display", children="9",
                                      className="stepper-value"),
                            html.Button("+", id="step-plus", n_clicks=0,
                                          className="stepper-btn"),
                        ]),
                        dcc.Slider(id="slider-passes", min=5, max=15,
                                    value=9, step=1, marks=None, tooltip=None,
                                    className="sad-slider hidden-slider"),
                    ]),
                    html.Div(id="reduction-display"),
                ]),
                html.Div(style={"margin-top": "12px"}, children=[
                    slider("slider-alpha", 4.0, 12.0, 6.0, 0.5,
                            "Angle des outillages 2α (°)", precision=1),
                ]),
            ]),
        ],
    ),

    # Conditions operatoires
    section_card("activity", "Conditions opératoires", None,
                  pill_text="Atelier", pill_type="neutral",
                  children=[
        html.Div(className="control-row", children=[
            slider("slider-vf", 0.5, 30.0, 15.0, 0.1,
                    "Vitesse de sortie (m/s)", precision=1),
            slider("slider-Tamb", 15, 45, 25, 1,
                    "Température atelier (°C)", precision=0),
        ]),
        html.Div(className="control-row", children=[
            slider("slider-shift", 4, 12, 8, 1,
                    "Durée du poste (h)", precision=0),
            slider("slider-oee", 0.40, 0.95, 0.75, 0.05,
                    "Rendement opérationnel", precision=2),
        ]),
        html.Div(style={"margin-top": "12px"}, children=[
            slider("slider-cooling", 0.0, 0.9, 0.6, 0.05,
                    "Refroidissement inter-passes η (cabestans + bain)",
                    precision=2),
        ]),
    ]),

    # Lubrifiant
    section_card("drop", "Lubrifiant", None,
                  pill_text="CTTD μ(T,t)", pill_type="warning",
                  children=[
        html.Label("Type de lubrifiant", className="control-label"),
        dcc.Dropdown(
            id="dropdown-lubricant",
            options=LUB_OPTIONS,
            value="savon_calcique",
            clearable=False,
            style={"margin-bottom": "16px"},
        ),
        html.Div(className="control-row", children=[
            slider("slider-mu0", 0.02, 0.10, 0.060, 0.005,
                    "Coefficient de frottement initial μ₀", precision=3),
            slider("slider-beta", 0.10, 0.50, 0.30, 0.01,
                    "Sensibilité thermique β", precision=2),
        ]),
        html.Div(className="control-row", children=[
            slider("slider-gamma", 0.1, 5.0, 1.5, 0.1,
                    "Vitesse de dégradation γ (×10⁻⁶)", precision=1),
            slider("slider-Qlub", 40000, 120000, 65000, 1000,
                    "Stabilité thermique Q (J/mol)", precision=0),
        ]),
        slider("slider-age", 0, 180, 30, 5,
               "Âge actuel du lubrifiant (jours)", precision=0),
    ]),

    # Validation
    html.Div(id="validation-output", style={"margin-top": "16px"}),

    # Continue button
    html.Div(style={"text-align": "center", "margin-top": "24px"}, children=[
        dcc.Link(
            html.Button([icon("arrow"), "  Continuer vers l'analyse"],
                        className="btn btn-gold btn-large"),
            href="/material",
        ),
    ]),

    footer(),
])


# ════════════════════════════════════════════════════════════════
# Callbacks
# ════════════════════════════════════════════════════════════════

@callback(
    Output("config-store", "data"),
    [Input("slider-K", "value"),
     Input("slider-n", "value"),
     Input("slider-d0", "value"),
     Input("slider-df", "value"),
     Input("slider-passes", "value"),
     Input("slider-alpha", "value"),
     Input("slider-vf", "value"),
     Input("slider-Tamb", "value"),
     Input("slider-shift", "value"),
     Input("slider-oee", "value"),
     Input("slider-cooling", "value"),
     Input("dropdown-lubricant", "value"),
     Input("slider-mu0", "value"),
     Input("slider-beta", "value"),
     Input("slider-gamma", "value"),
     Input("slider-Qlub", "value"),
     Input("slider-age", "value")],
    State("config-store", "data"),
)
def update_store(K, n, d0, df, passes, alpha, vf, Tamb, shift, oee, cooling,
                 lub_key, mu0, beta, gamma, Qlub, age, store):
    """Centralise tous les sliders dans le Store global."""
    store = store or {}
    try:
        passes = int(passes) if passes else 9
        alpha = float(alpha) if alpha is not None else 6.0
    except (TypeError, ValueError):
        passes, alpha = 9, 6.0

    store.update({
        "K": K, "n": n,
        "d_0": d0, "d_f": df, "n_passes": passes,
        "alpha_uniforme": alpha,
        "alphas": [alpha] * passes,
        "v_f": vf, "T_ambient_C": Tamb, "T_shift_h": shift, "eta_OEE": oee,
        "eta_cooling": cooling if cooling is not None else 0.6,
        "lubricant_key": lub_key,
        "mu_0": mu0, "beta": beta,
        "gamma": (gamma or 1.5) * 1e-6,
        "Q_lub": Qlub,
        "age_lubrifiant_jours": age,
    })

    # Invalider l'override de diametres reels si la geometrie a change
    # par rapport au preset LATRECA (l'utilisateur a touche d_0/d_f/passes).
    diam_override = store.get("diametres_reels")
    if isinstance(diam_override, (list, tuple)) and len(diam_override) > 0:
        if (abs(float(diam_override[0]) - float(d0)) > 1e-3
                or abs(float(diam_override[-1]) - float(df)) > 1e-3
                or len(diam_override) != int(passes) + 1):
            store.pop("diametres_reels", None)
            store.pop("_preset_actif", None)

    return store


@callback(
    Output("reduction-display", "children"),
    [Input("slider-d0", "value"), Input("slider-df", "value"),
     Input("slider-passes", "value")],
)
def update_reduction(d0, df, passes):
    """Affiche la reduction par passe estimee."""
    if d0 and df and passes and d0 > df:
        ratio_total = (d0 / df)
        ratio_par_passe = ratio_total ** (1 / int(passes))
        red_par_passe = (1 - 1 / ratio_par_passe ** 2) * 100
        return html.Div(className="info-box", children=[
            html.Div("RÉDUCTION PAR PASSE", className="info-box-label"),
            html.Div([
                html.Span("≈ "),
                html.Strong(f"{red_par_passe:.1f}"),
                html.Span(" %"),
                html.Span(" / passe", className="info-box-suffix"),
            ], className="info-box-value"),
        ])
    return None


@callback(
    Output("reduction-totale-pill", "children"),
    [Input("slider-d0", "value"), Input("slider-df", "value")],
)
def update_reduction_pill(d0, df):
    """Pill 'Réduction totale X%' en haut a droite de la card geometrie."""
    if d0 and df and d0 > df:
        red = (1 - (df / d0) ** 2) * 100
        return f"Réduction totale {red:.1f}%"
    return "Réduction —"


@callback(
    Output("step-display", "children"),
    [Input("slider-passes", "value")],
)
def update_step_display(v):
    return f"{int(v)}" if v else "9"


@callback(
    Output("slider-passes", "value"),
    [Input("step-plus", "n_clicks"),
     Input("step-minus", "n_clicks")],
    State("slider-passes", "value"),
    prevent_initial_call=True,
)
def step_buttons(plus, minus, current):
    from dash import ctx
    current = int(current or 9)
    if not ctx.triggered_id:
        return current
    if ctx.triggered_id == "step-plus":
        return min(current + 1, 15)
    return max(current - 1, 5)


@callback(
    [Output("slider-mu0", "value"),
     Output("slider-beta", "value"),
     Output("slider-gamma", "value"),
     Output("slider-Qlub", "value")],
    Input("dropdown-lubricant", "value"),
)
def update_lubricant_params(lub_key):
    """Auto-remplit les params CTTD depuis la base de lubrifiants."""
    if lub_key in LUBRICANTS:
        lub = LUBRICANTS[lub_key]
        return (lub.get("mu_0", 0.060),
                lub.get("beta", 0.30),
                lub.get("gamma", 1.5e-6) * 1e6,
                lub.get("Q_lub", 65000.0))
    return (0.060, 0.30, 1.5, 65000)


@callback(
    Output("validation-output", "children"),
    Input("config-store", "data"),
)
def validate_config(store):
    """Validation simple : d_0 > d_f."""
    if not store:
        return None
    if store.get("d_0", 0) <= store.get("d_f", 0):
        return alert("danger", "Configuration invalide",
                      "Le diamètre d'entrée doit être supérieur au diamètre de sortie.",
                      icon_name="alert")
    return alert(
        "success", "Configuration validée",
        "Vous pouvez maintenant explorer les modules d'analyse via la barre latérale.",
        icon_name="check",
    )


# ════════════════════════════════════════════════════════════════
# Preset LATRECA Reel (donnees collectees Avril 2026)
# ════════════════════════════════════════════════════════════════

# Diametres reels mesures par passe (fiche de collecte LATRECA)
LATRECA_DIAMETRES = [5.00, 4.40, 3.93, 3.51, 3.13, 2.81, 2.50, 2.23, 1.99, 1.78]

LATRECA_PRESET = {
    # Materiau
    "K": 335.0, "n": 0.50,
    # Geometrie reelle
    "d_0": 5.00, "d_f": 1.78, "n_passes": 9,
    "alpha_uniforme": 8.0,
    "alphas": [8.0] * 9,
    "diametres_reels": LATRECA_DIAMETRES,
    # Conditions operatoires (deduites)
    "v_f": 1.5, "T_ambient_C": 25,
    "T_shift_h": 8, "eta_OEE": 0.65,
    "eta_cooling": 0.40,  # ΔT eau = 2°C → refroidissement faible
    # Lubrifiant : huile minerale non filtree
    "lubricant_key": "huile_minerale_latreca",
    "mu_0": 0.055, "beta": 0.40, "gamma": 3.5e-6,
    "Q_lub": 65000.0,
    "age_lubrifiant_jours": 120,
    # Marqueur preset actif
    "_preset_actif": "latreca",
}


@callback(
    [Output("slider-K", "value", allow_duplicate=True),
     Output("slider-n", "value", allow_duplicate=True),
     Output("slider-d0", "value", allow_duplicate=True),
     Output("slider-df", "value", allow_duplicate=True),
     Output("slider-passes", "value", allow_duplicate=True),
     Output("slider-alpha", "value", allow_duplicate=True),
     Output("slider-vf", "value", allow_duplicate=True),
     Output("slider-Tamb", "value", allow_duplicate=True),
     Output("slider-shift", "value", allow_duplicate=True),
     Output("slider-oee", "value", allow_duplicate=True),
     Output("slider-cooling", "value", allow_duplicate=True),
     Output("dropdown-lubricant", "value", allow_duplicate=True),
     Output("slider-age", "value", allow_duplicate=True),
     Output("config-store", "data", allow_duplicate=True)],
    Input("btn-preset-latreca", "n_clicks"),
    State("config-store", "data"),
    prevent_initial_call=True,
)
def apply_latreca_preset(n_clicks, current):
    """Applique le preset LATRECA Reel (donnees terrain Avril 2026).

    Met a jour les sliders ET injecte dans le config-store les diametres
    reels mesures par passe + le marqueur de preset actif.
    """
    if not n_clicks:
        return (dash.no_update,) * 14
    p = LATRECA_PRESET
    # Fusionner avec le store actuel pour ne pas perdre d'autres cles
    new_store = (current or {}).copy()
    new_store.update({
        "K": p["K"], "n": p["n"],
        "d_0": p["d_0"], "d_f": p["d_f"],
        "n_passes": p["n_passes"],
        "alpha_uniforme": p["alpha_uniforme"],
        "alphas": p["alphas"],
        "diametres_reels": p["diametres_reels"],
        "v_f": p["v_f"], "T_ambient_C": p["T_ambient_C"],
        "T_shift_h": p["T_shift_h"], "eta_OEE": p["eta_OEE"],
        "eta_cooling": p["eta_cooling"],
        "lubricant_key": p["lubricant_key"],
        "mu_0": p["mu_0"], "beta": p["beta"],
        "gamma": p["gamma"], "Q_lub": p["Q_lub"],
        "age_lubrifiant_jours": p["age_lubrifiant_jours"],
        "_preset_actif": p["_preset_actif"],
    })
    return (p["K"], p["n"],
            p["d_0"], p["d_f"], p["n_passes"], p["alpha_uniforme"],
            p["v_f"], p["T_ambient_C"], p["T_shift_h"], p["eta_OEE"],
            p["eta_cooling"], p["lubricant_key"],
            p["age_lubrifiant_jours"],
            new_store)


# ════ Sliders → display value ════
for sid, fmt in [
    ("slider-K", lambda v: f"{v:.0f}"),
    ("slider-n", lambda v: f"{v:.2f}"),
    ("slider-d0", lambda v: f"{v:.2f}"),
    ("slider-df", lambda v: f"{v:.2f}"),
    ("slider-alpha", lambda v: f"{v:.1f}°"),
    ("slider-vf", lambda v: f"{v:.1f}"),
    ("slider-Tamb", lambda v: f"{int(v)}°C"),
    ("slider-shift", lambda v: f"{int(v)} h"),
    ("slider-oee", lambda v: f"{v:.2f}"),
    ("slider-cooling", lambda v: f"{v:.2f}"),
    ("slider-mu0", lambda v: f"{v:.3f}"),
    ("slider-beta", lambda v: f"{v:.2f}"),
    ("slider-gamma", lambda v: f"{v:.1f}"),
    ("slider-Qlub", lambda v: f"{int(v):,}".replace(",", " ")),
    ("slider-age", lambda v: f"{int(v)} j"),
]:
    @callback(
        Output({"type": "value-display", "id": sid}, "children"),
        Input(sid, "value"),
        prevent_initial_call=False,
    )
    def _update(v, _fmt=fmt):
        return _fmt(v) if v is not None else "—"
