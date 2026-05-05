"""
═══════════════════════════════════════════════════════════════════════
GENERATEUR DE RAPPORT PDF (reportlab)
═══════════════════════════════════════════════════════════════════════

Produit un rapport PDF complet de l'analyse en mode "memoire technique" :
    - Page de garde (titre, date, contexte)
    - Configuration courante (parametres)
    - Resultats simulation : KPIs + securite par contrainte
    - Tableau detail par passe
    - Resultat optimisation NSGA-II (si disponible) + comparaison
    - Diagnostic intelligent (verdict + actions ordonnees)

Pas d'import dash ici. Pas d'image (Plotly) pour eviter la dependance
kaleido. Tableaux et metriques uniquement (suffisant pour archivage).
═══════════════════════════════════════════════════════════════════════
"""

import base64
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from core.recommendations import diagnostic_global


# Charte couleurs SAD LATRECA
GOLD = colors.HexColor("#A38B3E")
DEEP_GREEN = colors.HexColor("#0A2A1F")
CORAL = colors.HexColor("#E07856")
MINT = colors.HexColor("#2EAE7F")
LIGHT_BG = colors.HexColor("#FAFAF7")
LINE = colors.HexColor("#E5DFCE")


def _styles():
    """Styles communs pour le rapport."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title", parent=base["Title"],
            fontName="Helvetica-Bold", fontSize=22,
            textColor=DEEP_GREEN, alignment=TA_LEFT,
            spaceAfter=4),
        "subtitle": ParagraphStyle(
            "Subtitle", parent=base["Normal"],
            fontName="Helvetica", fontSize=11,
            textColor=colors.HexColor("#5A6B62"),
            spaceAfter=20),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"],
            fontName="Helvetica-Bold", fontSize=14,
            textColor=DEEP_GREEN, spaceBefore=14, spaceAfter=8,
            borderPadding=4, leftIndent=0),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"],
            fontName="Helvetica-Bold", fontSize=11,
            textColor=GOLD, spaceBefore=10, spaceAfter=6),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"],
            fontName="Helvetica", fontSize=9.5,
            textColor=colors.HexColor("#1F2A26"),
            leading=13, spaceAfter=4),
        "small": ParagraphStyle(
            "Small", parent=base["Normal"],
            fontName="Helvetica", fontSize=8,
            textColor=colors.HexColor("#8A9690")),
        "kpi_label": ParagraphStyle(
            "KpiLabel", parent=base["Normal"],
            fontName="Helvetica", fontSize=8,
            textColor=colors.HexColor("#8A9690"),
            alignment=TA_CENTER),
        "kpi_value": ParagraphStyle(
            "KpiValue", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=16,
            textColor=DEEP_GREEN, alignment=TA_CENTER),
    }


def _kpi_table(kpis_data, securite):
    """Bloc 4 KPIs en grille pour le rapport."""
    s = _styles()
    rows = [[
        Paragraph("PRODUCTION", s["kpi_label"]),
        Paragraph("CONSO. SPÉCIF.", s["kpi_label"]),
        Paragraph("T° MAX", s["kpi_label"]),
        Paragraph("PUISSANCE", s["kpi_label"]),
    ], [
        Paragraph(f"{kpis_data['Z1_production_t_jour']:.1f} t/j",
                  s["kpi_value"]),
        Paragraph(f"{kpis_data['Z2_SEC_kWh_tonne']:.0f} kWh/t",
                  s["kpi_value"]),
        Paragraph(f"{kpis_data['T_max_C']:.0f} °C", s["kpi_value"]),
        Paragraph(f"{kpis_data['P_totale_kW']:.0f} kW", s["kpi_value"]),
    ]]
    table = Table(rows, colWidths=[42 * mm] * 4, rowHeights=[8 * mm, 14 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, LINE),
        ('GRID', (0, 0), (-1, -1), 0.3, LINE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return table


def _securite_table(securite):
    """Tableau des 4 contraintes."""
    s = _styles()
    c1 = securite['C1_mecanique']
    c2 = securite['C2_thermique']
    c3 = securite['C3_moteur']
    c4 = securite['C4_tribologique']

    def status(ok):
        return ("OK", MINT) if ok else ("VIOLEE", CORAL)

    s1, c_s1 = status(c1['ok'])
    s2, c_s2 = status(c2.get('securite_ok', False))
    s3, c_s3 = status(c3['ok'])
    s4, c_s4 = status(c4['ok'])

    rows = [
        ["Contrainte", "Description", "Valeur", "Statut"],
        ["C1", "Mécanique (σ_d/σ_y max)",
         f"{c1.get('marge', 0):.2f}", s1],
        ["C2", "Thermique (T_max)",
         f"{c2.get('T_max_C', 0):.0f} °C", s2],
        ["C3", "Capacité moteur",
         f"{c3.get('P_total_kW', 0):.0f} / "
         f"{c3.get('P_nominale_kW', 0):.0f} kW", s3],
        ["C4", "Tribologique (μ_max/μ₀)",
         f"{c4.get('ratio_max', 0):.2f}", s4],
    ]
    table = Table(rows, colWidths=[18 * mm, 70 * mm, 50 * mm, 28 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DEEP_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), GOLD),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.3, LINE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),
        ('TEXTCOLOR', (3, 1), (3, 1), c_s1),
        ('TEXTCOLOR', (3, 2), (3, 2), c_s2),
        ('TEXTCOLOR', (3, 3), (3, 3), c_s3),
        ('TEXTCOLOR', (3, 4), (3, 4), c_s4),
        ('FONTNAME', (3, 1), (3, -1), 'Helvetica-Bold'),
    ]))
    return table


def _detail_table(resultat):
    """Tableau detail par passe."""
    n = len(resultat['delta_T'])
    rows = [["Passe", "Ø sortie (mm)", "v (m/s)", "F (N)",
             "P (kW)", "ΔT (°C)", "T_cum (°C)", "μ"]]
    for i in range(n):
        rows.append([
            f"{i + 1}",
            f"{resultat['diametres'][i + 1]:.2f}",
            f"{resultat['vitesses'][i]:.2f}",
            f"{resultat['forces'][i]:.0f}",
            f"{resultat['puissances'][i] / 1000:.2f}",
            f"{resultat['delta_T'][i]:.1f}",
            f"{resultat['temperatures'][i + 1]:.1f}",
            f"{resultat['mu_par_passe'][i]:.4f}",
        ])
    table = Table(rows, colWidths=[15 * mm, 22 * mm, 18 * mm, 22 * mm,
                                     20 * mm, 18 * mm, 22 * mm, 18 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DEEP_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), GOLD),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.25, LINE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, LIGHT_BG]),
    ]))
    return table


def _comparaison_3way_table(actuel, optim, reference):
    """Tableau 3 voies Actuel / Optimisation / Reference."""
    rows = [
        ["Indicateur", "Actuel", "Optimisation", "Référence"],
        ["Vitesse (m/s)",
         f"{actuel['v']:.1f}",
         f"{optim['v']:.1f}" if optim else "—",
         f"{reference['vitesse']:.1f}"],
        ["Production (t/jour)",
         f"{actuel['prod']:.1f}",
         f"{optim['prod']:.1f}" if optim else "—",
         f"{reference['production']:.1f}"],
        ["Consommation (kWh/t)",
         f"{actuel['sec']:.0f}",
         f"{optim['sec']:.0f}" if optim else "—",
         f"{reference['consommation']:.0f}"],
        ["Température max (°C)",
         f"{actuel['T']:.0f}",
         f"{optim['T']:.0f}" if optim else "—",
         f"≤ {reference['temperature']:.0f}"],
    ]
    table = Table(rows, colWidths=[55 * mm, 35 * mm, 38 * mm, 38 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DEEP_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), GOLD),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 9.5),
        ('GRID', (0, 0), (-1, -1), 0.3, LINE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('TEXTCOLOR', (1, 1), (1, -1), CORAL),
        ('TEXTCOLOR', (2, 1), (2, -1), GOLD),
        ('TEXTCOLOR', (3, 1), (3, -1), MINT),
        ('FONTNAME', (1, 1), (-1, -1), 'Helvetica-Bold'),
    ]))
    return table


def _action_block(action, styles):
    """Bloc d'action recommandee (constat + actions + gain)."""
    sev_color = {
        "critique": CORAL,
        "vigilance": GOLD,
        "ok": MINT,
    }.get(action.get("severite", "ok"), GOLD)

    title = f"<b>[{action.get('module', '')}]</b> {action.get('titre', '')}"
    constat = action.get("constat", "")
    actions_list = action.get("actions", []) or []
    gain = action.get("gain_estime", "—")

    rows = [
        [Paragraph(title, styles["body"])],
        [Paragraph(f"<i>{constat}</i>", styles["body"])],
    ]
    for a in actions_list:
        rows.append([Paragraph(f"&bull; {a}", styles["body"])])
    rows.append([Paragraph(f"<b>Gain estimé :</b> {gain}", styles["small"])])

    table = Table(rows, colWidths=[170 * mm])
    table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, LINE),
        ('LINEBEFORE', (0, 0), (0, -1), 3, sev_color),
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return table


def generer_rapport_pdf(config, resultat, opt_store, reference):
    """
    Genere le rapport PDF complet et retourne les bytes encodes en base64
    (compatible avec dcc.Download).

    Parameters
    ----------
    config : dict
        Configuration (store global Dash).
    resultat : dict
        Sortie de simuler_scenario().
    opt_store : dict or None
        Resultat NSGA-II local a la page Analyse Globale.
    reference : dict
        Reference constructeur (REFERENCE).

    Returns
    -------
    str : contenu PDF encode base64.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="SAD LATRECA - Rapport d'analyse",
        author="SAD LATRECA",
    )
    styles = _styles()
    story = []

    # ─── Page de garde ───
    story.append(Paragraph("SAD LATRECA", styles["title"]))
    story.append(Paragraph(
        "Système d'Aide à la Décision · Ligne de tréfilage cuivre 9 passes",
        styles["subtitle"]))

    now = datetime.now().strftime("%d %B %Y · %H:%M")
    story.append(Paragraph(f"<b>Rapport généré le :</b> {now}", styles["body"]))
    story.append(Paragraph(
        "<b>Modèle :</b> Avitzur (force) + Hollomon (durcissement) + "
        "CTTD μ(T,t) + thermique adiabatique avec refroidissement inter-passes",
        styles["body"]))
    story.append(Spacer(1, 8 * mm))

    # ─── KPIs principaux ───
    story.append(Paragraph("Résumé exécutif", styles["h1"]))
    story.append(_kpi_table(resultat['KPIs'], resultat['securite']))
    story.append(Spacer(1, 6 * mm))

    # ─── Configuration ───
    story.append(Paragraph("Configuration appliquée", styles["h1"]))
    cfg_rows = [
        ["Matériau", f"K = {config.get('K', 335):.0f} MPa, "
                       f"n = {config.get('n', 0.5):.2f} (Cuivre ETP)"],
        ["Géométrie",
         f"Ø {config.get('d_0', 8):.1f} → {config.get('d_f', 2):.1f} mm, "
         f"{int(config.get('n_passes', 9))} passes, "
         f"2α = {config.get('alpha_uniforme', 6):.1f}°"],
        ["Vitesse de sortie", f"{config.get('v_f', 15):.1f} m/s"],
        ["Refroidissement η", f"{config.get('eta_cooling', 0.6):.2f}"],
        ["Lubrifiant",
         f"{config.get('lubricant_key', '—')}, "
         f"μ₀ = {config.get('mu_0', 0.06):.3f}, "
         f"âge = {int(config.get('age_lubrifiant_jours', 30))} j"],
    ]
    cfg_table = Table(cfg_rows, colWidths=[40 * mm, 130 * mm])
    cfg_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.3, LINE),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_BG),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(cfg_table)
    story.append(Spacer(1, 6 * mm))

    # ─── Securite ───
    story.append(Paragraph("Vérification des contraintes de sécurité",
                            styles["h1"]))
    story.append(_securite_table(resultat['securite']))
    story.append(Spacer(1, 6 * mm))

    # ─── Comparaison 3 voies ───
    actuel = {
        'v': float(config.get('v_f', 15.0)),
        'prod': float(resultat['KPIs']['Z1_production_t_jour']),
        'sec': float(resultat['KPIs']['Z2_SEC_kWh_tonne']),
        'T': float(resultat['KPIs']['T_max_C']),
    }
    optim = None
    if opt_store and opt_store.get('compromis'):
        c = opt_store['compromis']
        # T_max du compromis : pas dispose, on met '—'
        optim = {
            'v': float(c['v_f']),
            'prod': float(c['Z1_production_t_jour']),
            'sec': float(c['Z2_SEC_kWh_tonne']),
            'T': 0.0,  # placeholder
        }

    story.append(Paragraph("Comparaison 3 voies : Actuel · Optimisation · "
                            "Référence constructeur", styles["h1"]))
    story.append(_comparaison_3way_table(actuel, optim, reference))
    story.append(Spacer(1, 6 * mm))

    # ─── Saut de page ───
    story.append(PageBreak())

    # ─── Diagnostic intelligent ───
    diag = diagnostic_global(
        resultat, reference, opt_store,
        T_seuil=float(config.get('T_max_C', 140.0)))

    story.append(Paragraph("Diagnostic intelligent", styles["h1"]))
    sev = diag['severite_globale'].upper()
    sev_color = {
        "CRITIQUE": CORAL,
        "VIGILANCE": GOLD,
        "OK": MINT,
    }.get(sev, GOLD)

    verdict_t = Table([[
        Paragraph(f"<b>Sévérité globale :</b> {sev}", styles["body"]),
        Paragraph(diag['verdict'], styles["body"]),
    ]], colWidths=[40 * mm, 130 * mm])
    verdict_t.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, LINE),
        ('LINEBEFORE', (0, 0), (0, -1), 4, sev_color),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(verdict_t)
    story.append(Spacer(1, 6 * mm))

    if diag['actions']:
        story.append(Paragraph("Actions recommandées (par sévérité)",
                                styles["h2"]))
        for action in diag['actions']:
            story.append(_action_block(action, styles))
            story.append(Spacer(1, 3 * mm))
    else:
        story.append(Paragraph("Aucune action requise. La ligne fonctionne "
                                "dans la zone optimale.", styles["body"]))
    story.append(Spacer(1, 4 * mm))

    # ─── Detail par passe ───
    story.append(PageBreak())
    story.append(Paragraph("Détail par passe (résultats simulation couplée)",
                            styles["h1"]))
    story.append(_detail_table(resultat))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Les valeurs ci-dessus sont issues de la simulation séquentielle "
        "couplée (mécanique → thermique → tribologique) avec le coefficient "
        "de friction recalculé à chaque passe par le modèle CTTD μ(T,t).",
        styles["small"]))

    # ─── Footer ───
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        "SAD LATRECA · Plateforme d'optimisation industrielle · "
        f"v0.4.2 · {datetime.now().year}",
        styles["small"]))

    # ─── Build ───
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return base64.b64encode(pdf_bytes).decode("ascii")
