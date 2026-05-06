"""
Graphiques Plotly stylises avec la palette SAD LATRECA.
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ═══ Palette ═══
COLORS = {
    "ink":        "#0A2A1F",
    "ink-2":      "#143D2E",
    "gold":       "#D4A24C",
    "gold-deep":  "#B8862F",
    "gold-soft":  "#F2D89A",
    "mint":       "#6FD3A6",
    "mint-deep":  "#2EAE7F",
    "coral":      "#E07856",
    "blue":       "#4A8FB5",
    "cream":      "#F6F4EC",
    "surface":    "#FFFFFF",
    "line":       "#E5DFCE",
    "muted":      "#8A9690",
    "ink-soft":   "#4A5C53",
}


def _apply_theme(fig, height=380, show_legend=True):
    """Applique le theme SAD a un graphique Plotly."""
    fig.update_layout(
        plot_bgcolor=COLORS["surface"],
        paper_bgcolor=COLORS["surface"],
        font=dict(family="Inter", size=12, color=COLORS["ink"]),
        xaxis=dict(
            gridcolor="rgba(10,42,31,0.06)",
            zerolinecolor="rgba(10,42,31,0.12)",
            linecolor=COLORS["line"],
            title_font=dict(size=11, color=COLORS["ink-soft"]),
        ),
        yaxis=dict(
            gridcolor="rgba(10,42,31,0.06)",
            zerolinecolor="rgba(10,42,31,0.12)",
            linecolor=COLORS["line"],
            title_font=dict(size=11, color=COLORS["ink-soft"]),
        ),
        legend=dict(
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor=COLORS["line"],
            borderwidth=1,
            font=dict(size=11),
        ),
        margin=dict(l=50, r=20, t=20, b=45),
        height=height,
        showlegend=show_legend,
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=COLORS["ink"],
            font=dict(family="JetBrains Mono", size=11, color="white"),
            bordercolor=COLORS["gold"],
        ),
    )
    return fig


# ═══════════════════════════════════════════════════════════════
# SPARKLINE (mini-graphique pour KPI cards)
# ═══════════════════════════════════════════════════════════════

def sparkline(values, color=None, height=32):
    """Mini-courbe pour KPI cards."""
    if color is None:
        color = COLORS["gold"]
    fig = go.Figure(go.Scatter(
        x=list(range(len(values))),
        y=values,
        mode="lines",
        line=dict(color=color, width=1.8, shape="spline", smoothing=0.6),
        fill="tozeroy",
        fillcolor=f"rgba(212,162,76,0.15)" if color == COLORS["gold"] else "rgba(46,174,127,0.15)",
        hoverinfo="skip",
    ))
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        height=height,
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


# ═══════════════════════════════════════════════════════════════
# COURBE HOLLOMON (Module Materiau)
# ═══════════════════════════════════════════════════════════════

def hollomon_curve(K=335, n=0.5, current_eps=2.77, stages=None):
    """
    Courbe sigma = K * eps^n avec annotation 'Loi de Hollomon' et points de
    chaque etape (cercles ouverts comme dans le design cible).
    """
    eps = np.linspace(0.01, max(4, current_eps * 1.1), 200)
    sigma = K * eps ** n

    fig = go.Figure()

    # Aire sous courbe (gradient gold->ink)
    fig.add_trace(go.Scatter(
        x=eps, y=sigma, fill="tozeroy",
        fillcolor="rgba(212,162,76,0.12)",
        line=dict(color=COLORS["gold"], width=3, shape="spline"),
        name="Loi de Hollomon",
        hovertemplate="ε=%{x:.2f}<br>σ=%{y:.0f} MPa<extra></extra>",
    ))

    # Points par etape (cercles ouverts)
    if stages is None:
        stages = np.linspace(0.3, current_eps, 8)
    stages_sigma = [K * e ** n for e in stages]
    fig.add_trace(go.Scatter(
        x=list(stages), y=stages_sigma,
        mode="markers",
        marker=dict(
            size=11,
            color="white",
            line=dict(color=COLORS["ink"], width=2),
        ),
        showlegend=False,
        hovertemplate="ε=%{x:.2f}<br>σ=%{y:.0f} MPa<extra></extra>",
    ))

    # Point courant (sortie) en or
    cur_sigma = K * current_eps ** n
    fig.add_trace(go.Scatter(
        x=[current_eps], y=[cur_sigma],
        mode="markers",
        marker=dict(
            size=14, color=COLORS["gold"],
            line=dict(color=COLORS["ink"], width=2),
        ),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Annotation pill flottante (formule)
    fig.add_annotation(
        x=current_eps, y=cur_sigma,
        text=f"<b>σ={cur_sigma:.0f}</b> · ε={current_eps:.2f}",
        showarrow=False,
        xshift=80, yshift=10,
        bgcolor=COLORS["ink"],
        bordercolor=COLORS["gold"],
        borderwidth=1,
        borderpad=6,
        font=dict(family="JetBrains Mono", size=11, color="#F2D89A"),
    )
    # Annotation formule en haut a gauche
    fig.add_annotation(
        x=0.20, y=0.85, xref="paper", yref="paper",
        text=f"<b>Loi de Hollomon</b><br>σ = {K:.0f} · ε^{n:.2f}",
        showarrow=False,
        bgcolor="white",
        bordercolor=COLORS["line"],
        borderwidth=1,
        borderpad=10,
        font=dict(family="JetBrains Mono", size=11, color=COLORS["ink"]),
        align="left",
    )

    fig.update_xaxes(title="ε plastique vraie [—]")
    fig.update_yaxes(title="σ (MPa)")
    return _apply_theme(fig, height=420, show_legend=False)


# ═══════════════════════════════════════════════════════════════
# EVOLUTION RESISTANCE PAR ETAPE (bar chart)
# ═══════════════════════════════════════════════════════════════

def resistance_per_stage(profil):
    """Bar chart resistance par etape."""
    n = len(profil['contraintes_par_passe'])
    stages = list(range(n))
    sigmas = profil['contraintes_par_passe']

    fig = go.Figure(go.Bar(
        x=stages, y=sigmas,
        marker=dict(
            color=COLORS["gold"],
            line=dict(color=COLORS["gold-deep"], width=1),
        ),
        text=[f"{s:.0f}" for s in sigmas],
        textposition="outside",
        textfont=dict(family="JetBrains Mono", size=10, color=COLORS["ink"]),
        hovertemplate="Étape %{x}<br>σ_y=%{y:.0f} MPa<extra></extra>",
    ))
    fig.update_xaxes(title="Étape", dtick=1)
    fig.update_yaxes(title="Résistance σ_y (MPa)")
    return _apply_theme(fig, height=360, show_legend=False)


# ═══════════════════════════════════════════════════════════════
# DECOMPOSITION DES FORCES (stacked bar)
# ═══════════════════════════════════════════════════════════════

def force_decomposition(forces_def, forces_frot, forces_red):
    """Bar chart empile des composantes de force par etape."""
    n = len(forces_def)
    stages = list(range(1, n + 1))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=stages, y=forces_def, name="Déformation",
        marker_color=COLORS["ink"],
        hovertemplate="Étape %{x}<br>F_def=%{y:.0f} N<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=stages, y=forces_frot, name="Frottement",
        marker_color=COLORS["gold"],
        hovertemplate="Étape %{x}<br>F_frot=%{y:.0f} N<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=stages, y=forces_red, name="Interne",
        marker_color=COLORS["mint-deep"],
        hovertemplate="Étape %{x}<br>F_int=%{y:.0f} N<extra></extra>",
    ))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title="Étape", dtick=1)
    fig.update_yaxes(title="Force (N)")
    return _apply_theme(fig, height=380, show_legend=True)


def forces_per_stage(forces, label_prefix="P"):
    """
    Bar chart de la force totale par passe avec :
    - Premiere barre en OR (pic) + annotation 'Pic'
    - Autres barres en vert nuit
    - Valeurs au-dessus de chaque barre
    Reproduit le design cible (page 04 Forces).
    """
    n = len(forces)
    stages = [f"{label_prefix}{i+1}" for i in range(n)]
    pic_idx = forces.index(max(forces))
    colors = [
        COLORS["gold"] if i == pic_idx else COLORS["ink"]
        for i in range(n)
    ]
    line_colors = [
        COLORS["gold-deep"] if i == pic_idx else COLORS["ink-2"]
        for i in range(n)
    ]

    fig = go.Figure(go.Bar(
        x=stages, y=forces,
        marker=dict(color=colors,
                    line=dict(color=line_colors, width=1)),
        text=[f"{f:,.0f}".replace(",", " ") for f in forces],
        textposition="outside",
        textfont=dict(family="JetBrains Mono", size=11, color=COLORS["ink"]),
        hovertemplate="%{x}<br>F=%{y:,.0f} N<extra></extra>",
        showlegend=False,
    ))

    # Annotation 'Pic' au-dessus de la barre maximale
    fig.add_annotation(
        x=stages[pic_idx], y=forces[pic_idx],
        text="Pic",
        showarrow=False,
        yshift=30,
        bgcolor=COLORS["gold-soft"],
        bordercolor=COLORS["gold"],
        borderwidth=1,
        borderpad=4,
        font=dict(family="JetBrains Mono", size=10,
                   color=COLORS["gold-deep"], weight="bold"),
    )

    fig.update_xaxes(title="")
    fig.update_yaxes(title="Force (N)", showticklabels=False)
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=30))
    return _apply_theme(fig, height=380, show_legend=False)


# ═══════════════════════════════════════════════════════════════
# PROFIL THERMIQUE
# ═══════════════════════════════════════════════════════════════

def temperature_profile(T_cumulees, T_seuil=140.0):
    """Profil de temperature avec ligne de seuil."""
    n = len(T_cumulees)
    stages = list(range(n))
    T_max = max(T_cumulees)

    if T_max > T_seuil:
        line_color = COLORS["coral"]
    elif T_max > T_seuil - 30:
        line_color = COLORS["gold"]
    else:
        line_color = COLORS["mint-deep"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=stages, y=T_cumulees,
        mode="lines+markers",
        line=dict(color=line_color, width=3, shape="spline"),
        marker=dict(size=10, color=line_color, line=dict(color="white", width=2)),
        fill="tozeroy",
        fillcolor=f"rgba(212,162,76,0.10)",
        hovertemplate="Étape %{x}<br>T=%{y:.1f}°C<extra></extra>",
        name="Température",
    ))

    fig.add_hline(
        y=T_seuil,
        line=dict(dash="dash", color=COLORS["coral"], width=2),
        annotation_text=f"Seuil critique {T_seuil}°C",
        annotation_position="top right",
        annotation_font=dict(family="JetBrains Mono", size=10,
                              color=COLORS["coral"]),
    )

    fig.update_xaxes(title="Étape", dtick=1)
    fig.update_yaxes(title="Température (°C)")
    return _apply_theme(fig, height=360, show_legend=False)


# ═══════════════════════════════════════════════════════════════
# DELTA T PAR PASSE (bar chart)
# ═══════════════════════════════════════════════════════════════

def delta_t_per_stage(delta_T_list):
    """Bar chart de l'echauffement par etape."""
    stages = list(range(1, len(delta_T_list) + 1))

    fig = go.Figure(go.Bar(
        x=stages, y=delta_T_list,
        marker=dict(color=COLORS["coral"], opacity=0.85),
        text=[f"{t:.1f}" for t in delta_T_list],
        textposition="outside",
        textfont=dict(family="JetBrains Mono", size=10, color=COLORS["ink"]),
        hovertemplate="Étape %{x}<br>ΔT=%{y:.1f}°C<extra></extra>",
    ))
    fig.update_xaxes(title="Étape", dtick=1)
    fig.update_yaxes(title="ΔT (°C)")
    return _apply_theme(fig, height=320, show_legend=False)


# ═══════════════════════════════════════════════════════════════
# EVOLUTION DU LUBRIFIANT (mu vs temps)
# ═══════════════════════════════════════════════════════════════

def lubricant_evolution(temps_jours, mu_array, mu_initial, mu_critique,
                        nom="Lubrifiant actuel", age_actuel=None,
                        cycle_recommande=None):
    """
    Courbe duale : viscosite (or, decroissante) + frottement μ (coral, croissant).
    Lignes verticales de reference : 'Cycle recommandé' (vert) + 'Aujourd'hui' (coral).
    """
    import numpy as _np
    t = _np.array(temps_jours)
    mu = _np.array(mu_array)

    # Estime la viscosite residuelle (% du neuf) : decroit en miroir de mu
    visc_pct = 100 * _np.exp(-(mu - mu_initial) / max(mu_initial, 1e-9) * 0.7)
    visc_pct = _np.clip(visc_pct, 25, 100)

    fig = go.Figure()

    # Frottement μ (en %, normalise sur le seuil critique)
    mu_pct = 100 * mu / max(mu_critique, 1e-9) * 0.85
    fig.add_trace(go.Scatter(
        x=t, y=mu_pct,
        mode="lines+markers",
        line=dict(color=COLORS["coral"], width=2.5, shape="spline"),
        marker=dict(size=6, color="white",
                    line=dict(color=COLORS["coral"], width=2)),
        name="Frottement μ",
        hovertemplate="t=%{x:.0f}j<br>μ relatif=%{y:.0f}%<extra></extra>",
    ))

    # Viscosite residuelle
    fig.add_trace(go.Scatter(
        x=t, y=visc_pct,
        mode="lines+markers",
        line=dict(color=COLORS["gold"], width=2.5, shape="spline"),
        marker=dict(size=6, color="white",
                    line=dict(color=COLORS["gold"], width=2)),
        name="Viscosité",
        hovertemplate="t=%{x:.0f}j<br>visc=%{y:.0f}%<extra></extra>",
    ))

    # Reference verticale : cycle recommande
    if cycle_recommande is not None and cycle_recommande <= max(t):
        fig.add_vline(
            x=cycle_recommande,
            line=dict(dash="dash", color=COLORS["mint-deep"], width=1.5),
            annotation_text=f"Cycle recommandé · J{int(cycle_recommande)}",
            annotation_position="top left",
            annotation_font=dict(family="JetBrains Mono", size=10,
                                  color=COLORS["mint-deep"]),
        )

    # Reference verticale : aujourd'hui
    if age_actuel is not None and age_actuel <= max(t):
        fig.add_vrect(
            x0=age_actuel, x1=max(t),
            fillcolor=COLORS["coral"], opacity=0.06,
            line_width=0,
        )
        fig.add_vline(
            x=age_actuel,
            line=dict(dash="dash", color=COLORS["coral"], width=2),
            annotation_text=f"Aujourd'hui · J{int(age_actuel)}",
            annotation_position="top right",
            annotation_font=dict(family="JetBrains Mono", size=10,
                                  color=COLORS["coral"]),
        )

    fig.update_xaxes(title="Temps (jours)")
    fig.update_yaxes(title="% (visc. / μ relatif)", range=[0, 110])
    return _apply_theme(fig, height=380, show_legend=True)


# ═══════════════════════════════════════════════════════════════
# COMPARAISON LUBRIFIANTS
# ═══════════════════════════════════════════════════════════════

def lubricants_comparison(comparaison_resultats):
    """Compare plusieurs courbes mu(t)."""
    fig = go.Figure()
    palette = [COLORS["coral"], COLORS["gold"], COLORS["blue"], COLORS["mint-deep"]]

    for i, r in enumerate(comparaison_resultats):
        evol = r['evolution']
        fig.add_trace(go.Scatter(
            x=evol['temps_jours'], y=evol['mu_array'],
            mode="lines",
            name=r['nom'],
            line=dict(color=palette[i % len(palette)], width=2.5,
                      shape="spline"),
            hovertemplate=f"{r['nom']}<br>t=%{{x:.0f}}j<br>μ=%{{y:.4f}}<extra></extra>",
        ))

    fig.update_xaxes(title="Temps (jours)")
    fig.update_yaxes(title="Coefficient de frottement μ")
    return _apply_theme(fig, height=380, show_legend=True)


# ═══════════════════════════════════════════════════════════════
# FRONT DE PARETO
# ═══════════════════════════════════════════════════════════════

def pareto_front(pareto_solutions, points_remarquables=None,
                  point_actuel=None, point_reference=None):
    """
    Front de Pareto stylise (style maquette Streamlit) avec :
    - Courbe spline lisse passant par les solutions
    - Zone faisable verte ombree (en dessous de la courbe)
    - 3 points contextuels :
        * Actuel       (coral)
        * Optimal      (or, NSGA-II Compromis)
        * Reference    (vert)
    - Axe Y inverse (kWh/t bas = mieux, donc en haut visuellement)
    """
    sols_sorted = sorted(pareto_solutions,
                          key=lambda s: s['Z1_production_t_jour'])
    Z1 = [s['Z1_production_t_jour'] for s in sols_sorted]
    Z2 = [s['Z2_SEC_kWh_tonne'] for s in sols_sorted]

    fig = go.Figure()

    # ─── Zone faisable verte ombree ───
    # Polygone : sous la courbe Pareto (region atteignable)
    # Avec Y inverse : la zone s'etend de la courbe vers le BAS de l'axe
    # (= valeurs Z2 plus elevees), qui visuellement est en bas de l'ecran.
    if len(Z1) >= 2:
        # Etendre legerement les bords pour un meilleur rendu
        x_poly = ([Z1[0]] + Z1 + [Z1[-1]])
        y_max = max(Z2) * 1.15
        y_poly = ([y_max] + Z2 + [y_max])
        fig.add_trace(go.Scatter(
            x=x_poly, y=y_poly,
            fill="toself",
            fillcolor="rgba(46,174,127,0.12)",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
            name="Zone faisable",
        ))

    # ─── Courbe spline du front ───
    fig.add_trace(go.Scatter(
        x=Z1, y=Z2,
        mode="lines+markers",
        line=dict(color=COLORS["mint-deep"], width=2.5,
                  dash="dot", shape="spline", smoothing=1.0),
        marker=dict(size=10, color="white",
                    line=dict(color=COLORS["mint-deep"], width=2.5)),
        name="Front de Pareto",
        hovertemplate=("<b>Solution Pareto</b><br>"
                        "Production : %{x:.2f} t/j<br>"
                        "SEC : %{y:.0f} kWh/t<extra></extra>"),
    ))

    def _named_point(z1, z2, label, color, x_offset=0, y_offset=-30):
        """Ajoute un point + une etiquette avec fleche pointant vers lui."""
        fig.add_trace(go.Scatter(
            x=[z1], y=[z2],
            mode="markers",
            marker=dict(size=22, color=color,
                        line=dict(width=3, color="white")),
            showlegend=False,
            hovertemplate=(f"<b>{label}</b><br>"
                            f"%{{x:.2f}} t/j<br>"
                            f"%{{y:.0f}} kWh/t<extra></extra>"),
        ))
        fig.add_annotation(
            x=z1, y=z2, text=f"<b>{label}</b>",
            showarrow=True, arrowhead=0, arrowsize=1, arrowwidth=2,
            arrowcolor=color,
            ax=x_offset, ay=y_offset,
            bgcolor=color,
            bordercolor="white",
            borderwidth=2,
            borderpad=6,
            font=dict(family="JetBrains Mono", size=11, color="white"),
        )

    # Reference constructeur (en bas-droit, "cible")
    if point_reference:
        _named_point(point_reference.get('Z1', 25.0),
                      point_reference.get('Z2', 250.0),
                      "Réf. constr.", COLORS["mint-deep"],
                      x_offset=40, y_offset=-25)

    # Optimal (compromis NSGA-II sur le front)
    if points_remarquables:
        compromis = points_remarquables.get("compromis")
        if compromis:
            _named_point(compromis['Z1_production_t_jour'],
                          compromis['Z2_SEC_kWh_tonne'],
                          "Optimal", COLORS["gold"],
                          x_offset=0, y_offset=-40)

    # Actuel (point baseline reel)
    if point_actuel:
        _named_point(point_actuel.get('Z1', 18.0),
                      point_actuel.get('Z2', 320.0),
                      "Actuel", COLORS["coral"],
                      x_offset=-30, y_offset=30)

    # Annotation flottante : direction d'amelioration
    if len(Z1) >= 2:
        x_mid = (min(Z1) + max(Z1)) / 2
        y_mid = (min(Z2) + max(Z2)) / 2
        fig.add_annotation(
            x=x_mid, y=y_mid,
            text="↗ Amélioration",
            showarrow=False,
            font=dict(family="Inter", size=11,
                      color=COLORS["mint-deep"]),
            opacity=0.6,
        )

    fig.update_xaxes(title="Production journalière (t/jour)")
    fig.update_yaxes(title="Consommation énergétique (kWh/tonne)",
                      autorange="reversed")
    return _apply_theme(fig, height=440, show_legend=False)


# ═══════════════════════════════════════════════════════════════
# COMPARAISON DE SCENARIOS (subplots)
# ═══════════════════════════════════════════════════════════════

def scenarios_comparison(scenarios_data):
    """Subplot 2 colonnes : Production / Consommation."""
    names = list(scenarios_data.keys())
    Z1 = [d['Z1'] for d in scenarios_data.values()]
    Z2 = [d['Z2'] for d in scenarios_data.values()]

    fig = make_subplots(rows=1, cols=2,
                         subplot_titles=("Production (t/jour)",
                                          "Consommation (kWh/t)"))

    fig.add_trace(go.Bar(
        x=names, y=Z1, marker_color=COLORS["mint-deep"],
        text=[f"{v:.1f}" for v in Z1], textposition="outside",
        textfont=dict(family="JetBrains Mono", size=11),
        hovertemplate="%{x}<br>%{y:.2f} t/j<extra></extra>",
        showlegend=False,
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=names, y=Z2, marker_color=COLORS["gold"],
        text=[f"{v:.0f}" for v in Z2], textposition="outside",
        textfont=dict(family="JetBrains Mono", size=11),
        hovertemplate="%{x}<br>%{y:.2f} kWh/t<extra></extra>",
        showlegend=False,
    ), row=1, col=2)

    return _apply_theme(fig, height=340, show_legend=False)


# ═══════════════════════════════════════════════════════════════
# DIAMETRES SUCCESSIFS
# ═══════════════════════════════════════════════════════════════

def diameter_evolution(diametres):
    """Decroissance des diametres."""
    n = len(diametres)
    fig = go.Figure(go.Scatter(
        x=list(range(n)), y=diametres,
        mode="lines+markers",
        line=dict(color=COLORS["ink"], width=3, shape="spline"),
        marker=dict(size=10, color=COLORS["gold"],
                    line=dict(color=COLORS["ink"], width=2)),
        fill="tozeroy",
        fillcolor="rgba(212,162,76,0.10)",
        text=[f"{d:.2f}mm" for d in diametres],
        hovertemplate="Étape %{x}<br>Ø=%{y:.2f} mm<extra></extra>",
    ))
    fig.update_xaxes(title="Étape", dtick=1)
    fig.update_yaxes(title="Diamètre (mm)")
    return _apply_theme(fig, height=320, show_legend=False)


# ═══════════════════════════════════════════════════════════════
# CONVERGENCE NSGA-II : evolution generation par generation
# ═══════════════════════════════════════════════════════════════

def convergence_chart(history):
    """
    Trace la convergence de NSGA-II generation par generation.

    history : dict provenant de lancer_optimisation()['history']
        - generation : list[int]
        - best_Z1, mean_Z1 : evolution production [t/jour]
        - best_Z2, mean_Z2 : evolution SEC [kWh/tonne]
        - n_feasible : nb d'individus respectant les contraintes
        - n_pareto : taille du front non-domine

    Affiche 2 sous-graphiques (3 axes Y) :
        Haut : Z1 et Z2 (best + moyennes)
        Bas  : nombre d'individus faisables et taille du front Pareto
    """
    if not history or not history.get("generation"):
        # Figure vide en cas d'absence de donnees
        fig = go.Figure()
        fig.add_annotation(text="Aucun historique disponible",
                           xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False,
                           font=dict(family="Inter", size=14,
                                     color=COLORS["muted"]))
        return _apply_theme(fig, height=320, show_legend=False)

    gens = history["generation"]
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.10,
        row_heights=[0.65, 0.35],
        subplot_titles=(
            "Évolution des objectifs · meilleur faisable + moyenne population",
            "Diversité & faisabilité par génération",
        ),
        specs=[[{"secondary_y": True}],
               [{"secondary_y": True}]],
    )

    # --- Ligne 1 : Z1 (production) sur axe gauche, Z2 (SEC) sur axe droit ---
    fig.add_trace(go.Scatter(
        x=gens, y=history["best_Z1"], name="Best Z₁ (prod.)",
        mode="lines+markers",
        line=dict(color=COLORS["mint-deep"], width=3),
        marker=dict(size=6, color=COLORS["mint-deep"]),
        hovertemplate="Gen %{x}<br>Best prod : %{y:.2f} t/j<extra></extra>",
    ), row=1, col=1, secondary_y=False)

    fig.add_trace(go.Scatter(
        x=gens, y=history["mean_Z1"], name="Moyenne Z₁",
        mode="lines",
        line=dict(color=COLORS["mint-deep"], width=1, dash="dot"),
        opacity=0.5,
        hovertemplate="Gen %{x}<br>Moy prod : %{y:.2f} t/j<extra></extra>",
    ), row=1, col=1, secondary_y=False)

    fig.add_trace(go.Scatter(
        x=gens, y=history["best_Z2"], name="Best Z₂ (SEC)",
        mode="lines+markers",
        line=dict(color=COLORS["gold-deep"], width=3),
        marker=dict(size=6, color=COLORS["gold-deep"]),
        hovertemplate="Gen %{x}<br>Best SEC : %{y:.0f} kWh/t<extra></extra>",
    ), row=1, col=1, secondary_y=True)

    fig.add_trace(go.Scatter(
        x=gens, y=history["mean_Z2"], name="Moyenne Z₂",
        mode="lines",
        line=dict(color=COLORS["gold-deep"], width=1, dash="dot"),
        opacity=0.5,
        hovertemplate="Gen %{x}<br>Moy SEC : %{y:.0f} kWh/t<extra></extra>",
    ), row=1, col=1, secondary_y=True)

    # --- Ligne 2 : faisabilite + taille Pareto ---
    fig.add_trace(go.Bar(
        x=gens, y=history["n_feasible"], name="N faisables",
        marker_color=COLORS["mint"],
        opacity=0.7,
        hovertemplate="Gen %{x}<br>%{y} individus faisables<extra></extra>",
    ), row=2, col=1, secondary_y=False)

    fig.add_trace(go.Scatter(
        x=gens, y=history["n_pareto"], name="Taille Pareto",
        mode="lines+markers",
        line=dict(color=COLORS["coral"], width=2.5),
        marker=dict(size=6, color=COLORS["coral"]),
        hovertemplate="Gen %{x}<br>Pareto : %{y} solutions<extra></extra>",
    ), row=2, col=1, secondary_y=True)

    # Axes
    fig.update_yaxes(title_text="Production Z₁ (t/jour)",
                     color=COLORS["mint-deep"], row=1, col=1,
                     secondary_y=False)
    fig.update_yaxes(title_text="SEC Z₂ (kWh/tonne)",
                     color=COLORS["gold-deep"], row=1, col=1,
                     secondary_y=True)
    fig.update_yaxes(title_text="N faisables",
                     color=COLORS["mint"], row=2, col=1,
                     secondary_y=False)
    fig.update_yaxes(title_text="Taille Pareto",
                     color=COLORS["coral"], row=2, col=1,
                     secondary_y=True)
    fig.update_xaxes(title_text="Génération", row=2, col=1)

    return _apply_theme(fig, height=520, show_legend=True)
