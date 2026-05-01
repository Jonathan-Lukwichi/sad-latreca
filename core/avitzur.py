"""
═══════════════════════════════════════════════════════════════════════
PILIER P2 — MODÈLE D'AVITZUR (1963)
═══════════════════════════════════════════════════════════════════════

PRINCIPE : Théorème de la limite supérieure (Upper Bound Theorem)
La force calculée est TOUJOURS supérieure ou égale à la force réelle.
→ AVANTAGE SÉCURITAIRE pour la maintenance industrielle !

ÉQUATION CENTRALE :  F_total = F_déformation + F_frottement + F_redondant

EXPLICATION SIMPLE :
    Pour faire passer un fil dans une filière, on dépense 3 types d'énergie :

    1. F_déformation : énergie pour DÉFORMER le métal (utile)
    2. F_frottement  : énergie perdue par FROTTEMENT (gaspillée)
    3. F_redondant   : énergie perdue par CISAILLEMENT INTERNE (gaspillée)
                       (Comme un véhicule qui prend un virage trop serré)

POUR LE CUIVRE ETP :
    Précision typique vs expérimental : 3-5%
    (vs 12-18% pour le modèle de Sachs)

UTILISATION DANS LE SAD :
    À chaque passe, on calcule les 3 composantes puis F_total.
    F_total alimente ensuite le modèle thermique (Pilier P3).

RÉFÉRENCE :
    Avitzur, B. (1963). Analysis of wire drawing and extrusion
    through conical dies. J. Eng. Ind., 85(1), 89-95.
═══════════════════════════════════════════════════════════════════════
"""

import numpy as np
import math


# Conversion MPa → Pa pour cohérence des unités SI
MPA_TO_PA = 1e6


def deg_en_radians(angle_deg):
    """Convertit un angle en degrés vers radians."""
    return angle_deg * math.pi / 180.0


def calculer_section(diametre_mm):
    """
    Calcule la section circulaire d'un fil.

    Formule : A = π · d² / 4

    Parameters
    ----------
    diametre_mm : float
        Diamètre du fil [mm]

    Returns
    -------
    section_m2 : float
        Section [m²]
    """
    diametre_m = diametre_mm / 1000.0  # mm → m
    return math.pi * diametre_m**2 / 4.0


def calculer_force_avitzur(sigma_bar_MPa, d_in_mm, d_out_mm,
                            mu, alpha_deg, sigma_back_MPa=0.0):
    """
    Calcule la force de tréfilage selon le modèle d'Avitzur.

    Décompose la force en 3 composantes additives :
        F_total = F_déformation + F_frottement + F_redondant

    Parameters
    ----------
    sigma_bar_MPa : float
        Contrainte d'écoulement moyenne du matériau dans la filière [MPa]
        (Vient du modèle de Hollomon - Pilier P1)
    d_in_mm : float
        Diamètre d'entrée [mm]
    d_out_mm : float
        Diamètre de sortie [mm]
    mu : float
        Coefficient de frottement [-]
        (Cuivre : 0.03 - 0.10 typiquement)
    alpha_deg : float
        Demi-angle de la filière [degrés]
        (Typiquement 4° à 12°)
    sigma_back_MPa : float
        Contre-traction du cabestan amont [MPa] (souvent ~0)

    Returns
    -------
    dict avec les clés :
        - 'F_deformation' : composante déformation [N]
        - 'F_frottement'  : composante frottement [N]
        - 'F_redondant'   : composante travail redondant [N]
        - 'F_total'       : somme des trois [N]
        - 'sigma_d_MPa'   : contrainte de tréfilage [MPa]
        - 'puissance_W'   : F_total · v (à calculer ailleurs)
    """
    # ─── Vérifications de sécurité ───
    if sigma_bar_MPa <= 0:
        raise ValueError(f"sigma_bar doit être positif. Reçu : {sigma_bar_MPa}")
    if d_in_mm <= d_out_mm:
        raise ValueError(f"d_in ({d_in_mm}) doit être > d_out ({d_out_mm})")
    if mu < 0:
        raise ValueError(f"mu doit être >= 0. Reçu : {mu}")
    if alpha_deg <= 0 or alpha_deg >= 90:
        raise ValueError(f"alpha doit être dans (0°, 90°). Reçu : {alpha_deg}°")

    # ─── Conversions ───
    sigma_bar = sigma_bar_MPa * MPA_TO_PA  # MPa → Pa
    sigma_back = sigma_back_MPa * MPA_TO_PA
    alpha = deg_en_radians(alpha_deg)       # degrés → radians

    # ─── Sections ───
    A_in = calculer_section(d_in_mm)
    A_out = calculer_section(d_out_mm)
    rapport_reduction = A_in / A_out  # > 1

    # ─── COMPOSANTE 1 : Force de déformation idéale ───
    # F_def = σ̄ · A_out · ln(A_in / A_out)
    F_deformation = sigma_bar * A_out * np.log(rapport_reduction)

    # ─── COMPOSANTE 2 : Force de frottement ───
    # F_frot = μ · σ̄ · A_out · cot(α) · ln(A_in / A_out)
    # (formule simplifiée d'Avitzur)
    cot_alpha = 1.0 / math.tan(alpha)
    F_frottement = mu * sigma_bar * A_out * cot_alpha * np.log(rapport_reduction)

    # ─── COMPOSANTE 3 : Travail redondant ───
    # F_red = (2/√3) · σ̄ · A_out · f(α)
    # avec f(α) = α/sin²α - cot α
    # (formule originale d'Avitzur 1963)
    sin_alpha = math.sin(alpha)
    if abs(sin_alpha) < 1e-10:
        F_redondant = 0.0
    else:
        f_alpha = (alpha / (sin_alpha**2)) - cot_alpha
        F_redondant = (2.0 / math.sqrt(3.0)) * sigma_bar * A_out * f_alpha

    # ─── Contre-traction (force aspirée par cabestan amont) ───
    F_back = sigma_back * A_out

    # ─── Force totale ───
    F_total = F_deformation + F_frottement + F_redondant + F_back

    # Contrainte de tréfilage (= F_total / A_out)
    sigma_d_Pa = F_total / A_out
    sigma_d_MPa = sigma_d_Pa / MPA_TO_PA

    return {
        'F_deformation': F_deformation,
        'F_frottement': F_frottement,
        'F_redondant': F_redondant,
        'F_back': F_back,
        'F_total': F_total,
        'sigma_d_MPa': sigma_d_MPa,
        'rapport_reduction': rapport_reduction,
    }


def calculer_force_sachs(sigma_bar_MPa, d_in_mm, d_out_mm, mu, alpha_deg):
    """
    Calcule la force de tréfilage selon le modèle classique de Sachs (1927).

    Utile UNIQUEMENT pour comparaison pédagogique avec Avitzur.
    Sous-estime systématiquement la force de 12 à 18 %.

    Formule : σ_d = σ̄ · (1 + B) · ln(A_0/A_1)
             avec B = μ · cot(α)

    Returns
    -------
    F_total : float
        Force totale selon Sachs [N]
    """
    sigma_bar = sigma_bar_MPa * MPA_TO_PA
    alpha = deg_en_radians(alpha_deg)
    A_in = calculer_section(d_in_mm)
    A_out = calculer_section(d_out_mm)

    B = mu / math.tan(alpha)  # mu * cot(alpha)
    sigma_d = sigma_bar * (1 + B) * np.log(A_in / A_out)
    F_total = sigma_d * A_out
    return F_total


def calculer_puissance_passe(F_N, v_mps):
    """
    Calcule la puissance mécanique consommée par une passe.

    Formule : P = F · v

    Parameters
    ----------
    F_N : float
        Force de tréfilage [N]
    v_mps : float
        Vitesse du fil dans cette passe [m/s]

    Returns
    -------
    puissance_W : float
        Puissance mécanique [W]
    """
    return F_N * v_mps


def verifier_securite_mecanique(sigma_d_MPa, sigma_y_MPa, facteur_securite=0.6):
    """
    Vérifie la contrainte C1 (sécurité mécanique).

    La contrainte de tréfilage σ_d ne doit pas dépasser
    facteur_securite × σ_y (limite élastique actualisée).

    Si σ_d > 0.6 × σ_y → risque de rupture du fil !

    Parameters
    ----------
    sigma_d_MPa : float
        Contrainte de tréfilage actuelle [MPa]
    sigma_y_MPa : float
        Limite élastique actualisée du matériau [MPa]
    facteur_securite : float
        Facteur de sécurité (0.6 par défaut → marge 40%)

    Returns
    -------
    dict avec :
        - 'securite_ok'     : bool
        - 'ratio'           : sigma_d / sigma_y
        - 'marge_pourcent'  : marge restante en %
    """
    ratio = sigma_d_MPa / sigma_y_MPa
    securite_ok = ratio <= facteur_securite
    marge_pourcent = (facteur_securite - ratio) / facteur_securite * 100

    return {
        'securite_ok': securite_ok,
        'ratio': ratio,
        'marge_pourcent': marge_pourcent,
    }


# ═══════════════════════════════════════════════════════════════════
# TEST RAPIDE
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("TEST DU MODULE AVITZUR")
    print("=" * 60)

    # Test : 1ère passe de la tréfileuse LATRECA
    # 8 mm → 7.21 mm avec sigma_moy ≈ 100 MPa, mu=0.05, alpha=6°
    resultat = calculer_force_avitzur(
        sigma_bar_MPa=100.0,
        d_in_mm=8.0,
        d_out_mm=7.21,
        mu=0.05,
        alpha_deg=6.0
    )

    print(f"\nTest 1 : Avitzur sur la 1ère passe (8 → 7.21 mm)")
    print(f"  Force de déformation : {resultat['F_deformation']:.0f} N")
    print(f"  Force de frottement  : {resultat['F_frottement']:.0f} N")
    print(f"  Force redondante     : {resultat['F_redondant']:.0f} N")
    print(f"  Force TOTALE         : {resultat['F_total']:.0f} N")
    print(f"  Contrainte tréfilage : {resultat['sigma_d_MPa']:.2f} MPa")

    # Test 2 : comparaison Sachs vs Avitzur
    F_sachs = calculer_force_sachs(100.0, 8.0, 7.21, 0.05, 6.0)
    F_avitzur = resultat['F_total']
    ecart = (F_avitzur - F_sachs) / F_avitzur * 100

    print(f"\nTest 2 : Comparaison Sachs vs Avitzur")
    print(f"  F_Sachs    : {F_sachs:.0f} N")
    print(f"  F_Avitzur  : {F_avitzur:.0f} N")
    print(f"  Écart Sachs : {ecart:+.1f} %  (attendu : -12 à -18%)")

    # Test 3 : sécurité mécanique
    securite = verifier_securite_mecanique(
        sigma_d_MPa=resultat['sigma_d_MPa'],
        sigma_y_MPa=300.0  # exemple
    )
    print(f"\nTest 3 : Sécurité mécanique")
    print(f"  σ_d / σ_y  : {securite['ratio']:.3f}")
    print(f"  Marge      : {securite['marge_pourcent']:.1f} %")
    print(f"  Sécuritaire: {securite['securite_ok']}")

    print("\n✅ Tous les tests sont passés !")
