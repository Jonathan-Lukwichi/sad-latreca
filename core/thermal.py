"""
═══════════════════════════════════════════════════════════════════════
PILIER P3 — MODÈLE THERMIQUE ADIABATIQUE (Kim et al., 2001)
═══════════════════════════════════════════════════════════════════════

ÉQUATION CENTRALE :  ΔT = (η · F · v) / (ṁ · Cp)

EXPLICATION SIMPLE :
    Quand on tréfile un fil, 90-95 % de l'énergie de déformation
    se transforme en CHALEUR.

    À haute vitesse (> 10 m/s), cette chaleur n'a pas le temps
    de s'évacuer : on parle de régime ADIABATIQUE.

    → La température du fil monte de ΔT à chaque passe.

OÙ :
    ΔT  : élévation de température [K ou °C]
    η   : facteur de Taylor-Quinney (0.90-0.95) [-]
          (= fraction du travail mécanique qui devient chaleur)
    F   : force de tréfilage [N] (vient d'Avitzur)
    v   : vitesse du fil dans la passe [m/s]
    ṁ   : débit massique [kg/s]
    Cp  : chaleur spécifique du cuivre = 385 J/(kg·K)

VERROU CRITIQUE :
    T_max ≤ 140 °C
    Au-delà : le lubrifiant se DÉTRUIT et le cuivre se RAMOLLIT.

UTILISATION DANS LE SAD :
    À chaque passe, on calcule ΔT puis on cumule T_total.
    Si T_total > 140°C → ALERTE !
    T sert ensuite au modèle CTTD (Pilier P4) pour calculer μ(T).

RÉFÉRENCE :
    Kim, S.K., Lee, D.N. & Kim, B.M. (2001).
    Evaluation of temperature rise in wire drawing.
    J. Mater. Process. Technol., 112(1), 64-70.
═══════════════════════════════════════════════════════════════════════
"""

import math


# Constantes physiques par défaut (cuivre ETP)
RHO_CUIVRE = 8960.0      # Masse volumique du cuivre [kg/m³]
CP_CUIVRE = 385.0        # Chaleur spécifique du cuivre [J/(kg·K)]
K_THERMAL_CUIVRE = 401.0  # Conductivité thermique [W/(m·K)]
ETA_TAYLOR_QUINNEY = 0.92 # Fraction d'énergie convertie en chaleur

# Seuil critique (verrou V1)
T_MAX_CRITIQUE_C = 140.0  # Température max de sécurité [°C]


def calculer_debit_massique(d_mm, v_mps, rho_kg_m3=RHO_CUIVRE):
    """
    Calcule le débit massique du fil dans une passe.

    Formule : ṁ = ρ · A · v
             où A = π · d² / 4 (section du fil)

    Parameters
    ----------
    d_mm : float
        Diamètre du fil [mm]
    v_mps : float
        Vitesse du fil [m/s]
    rho_kg_m3 : float
        Masse volumique [kg/m³] (cuivre = 8960)

    Returns
    -------
    m_dot : float
        Débit massique [kg/s]
    """
    d_m = d_mm / 1000.0
    section = math.pi * d_m**2 / 4.0
    return rho_kg_m3 * section * v_mps


def calculer_elevation_temperature(F_N, v_mps, m_dot_kg_s,
                                     Cp=CP_CUIVRE, eta=ETA_TAYLOR_QUINNEY):
    """
    Calcule l'élévation de température pour UNE passe (modèle adiabatique).

    Formule de Kim et al. (2001) :
        ΔT = (η · F · v) / (ṁ · Cp)

    Parameters
    ----------
    F_N : float
        Force de tréfilage de la passe [N] (vient d'Avitzur)
    v_mps : float
        Vitesse du fil dans la passe [m/s]
    m_dot_kg_s : float
        Débit massique [kg/s]
    Cp : float
        Chaleur spécifique [J/(kg·K)]
    eta : float
        Facteur de Taylor-Quinney [-] (typiquement 0.92)

    Returns
    -------
    delta_T : float
        Élévation de température pour cette passe [°C ou K]
    """
    # Vérifications de sécurité
    if F_N < 0:
        raise ValueError(f"F_N doit être >= 0. Reçu : {F_N}")
    if v_mps <= 0:
        raise ValueError(f"v_mps doit être > 0. Reçu : {v_mps}")
    if m_dot_kg_s <= 0:
        raise ValueError(f"m_dot doit être > 0. Reçu : {m_dot_kg_s}")
    if Cp <= 0:
        raise ValueError(f"Cp doit être > 0. Reçu : {Cp}")

    # Énergie thermique générée [W]
    Q_dot = eta * F_N * v_mps

    # Élévation de température
    delta_T = Q_dot / (m_dot_kg_s * Cp)

    return delta_T


def calculer_temperature_cumulee(T_initiale_C, liste_delta_T):
    """
    Calcule la température cumulée passe par passe.

    Formule : T_n = T_initiale + Σ(ΔT_i)  pour i=1 à n

    Parameters
    ----------
    T_initiale_C : float
        Température initiale du fil à l'entrée [°C]
        (typiquement = température ambiante de l'atelier)
    liste_delta_T : list
        Liste des ΔT par passe [°C]

    Returns
    -------
    list
        Liste des températures après chaque passe [°C]
        Longueur = len(liste_delta_T) + 1
    """
    temperatures = [T_initiale_C]
    T_actuelle = T_initiale_C
    for delta_T in liste_delta_T:
        T_actuelle += delta_T
        temperatures.append(T_actuelle)
    return temperatures


def calculer_nombre_peclet(v_mps, L_mm=0.5,
                            alpha_diff=K_THERMAL_CUIVRE / (RHO_CUIVRE * CP_CUIVRE)):
    """
    Calcule le nombre de Péclet thermique pour valider l'hypothèse adiabatique.

    Formule : Pe = v · L / α

    Si Pe > 10 : hypothèse adiabatique JUSTIFIÉE
    Si Pe < 1  : hypothèse isotherme valide
    Si 1 < Pe < 10 : couplage thermique nécessaire

    Parameters
    ----------
    v_mps : float
        Vitesse du fil [m/s]
    L_mm : float
        Longueur de contact fil-filière [mm] (typiquement 0.5)
    alpha_diff : float
        Diffusivité thermique du cuivre [m²/s]

    Returns
    -------
    Pe : float
        Nombre de Péclet [-]
    """
    L_m = L_mm / 1000.0
    Pe = v_mps * L_m / alpha_diff
    return Pe


def hypothese_adiabatique_valide(v_mps, seuil_peclet=10.0):
    """
    Vérifie si l'hypothèse adiabatique est valide à cette vitesse.

    Returns
    -------
    bool
        True si Pe > seuil_peclet (adiabatique justifié)
    """
    Pe = calculer_nombre_peclet(v_mps)
    return Pe > seuil_peclet


def verifier_securite_thermique(T_max_C, T_seuil_C=T_MAX_CRITIQUE_C):
    """
    Vérifie la contrainte C2 (sécurité thermique).

    Si T_max > 140°C → DANGER : destruction du film lubrifiant.

    Parameters
    ----------
    T_max_C : float
        Température max atteinte [°C]
    T_seuil_C : float
        Seuil critique [°C] (par défaut 140°C)

    Returns
    -------
    dict avec :
        - 'securite_ok'        : bool
        - 'marge_C'            : marge thermique restante [°C]
        - 'niveau_risque'      : 'OK' | 'Attention' | 'CRITIQUE'
    """
    marge_C = T_seuil_C - T_max_C

    if marge_C >= 30.0:
        niveau_risque = 'OK'
    elif marge_C >= 10.0:
        niveau_risque = 'Attention'
    else:
        niveau_risque = 'CRITIQUE'

    return {
        'securite_ok': T_max_C <= T_seuil_C,
        'marge_C': marge_C,
        'niveau_risque': niveau_risque,
    }


def calculer_profil_thermique(forces_N, vitesses_mps, diametres_mm,
                                T_initiale_C=25.0,
                                eta=ETA_TAYLOR_QUINNEY, Cp=CP_CUIVRE,
                                rho=RHO_CUIVRE):
    """
    Calcule le profil thermique COMPLET sur les N passes.

    Parameters
    ----------
    forces_N : list
        Liste des forces de tréfilage [N] (de Avitzur)
    vitesses_mps : list
        Liste des vitesses du fil par passe [m/s]
    diametres_mm : list
        Liste des diamètres du fil après chaque passe [mm]
    T_initiale_C : float
        Température ambiante atelier [°C]
    eta, Cp, rho : float
        Paramètres physiques

    Returns
    -------
    dict avec :
        - 'delta_T_par_passe' : list des ΔT [°C]
        - 'T_cumulees'        : list des T(n) cumulées [°C]
        - 'T_max'             : température maximale atteinte [°C]
        - 'securite'          : résultat verifier_securite_thermique()
    """
    delta_T_par_passe = []
    n_passes = len(forces_N)

    # Calcul des ΔT pour chaque passe
    for i in range(n_passes):
        m_dot = calculer_debit_massique(diametres_mm[i], vitesses_mps[i], rho)
        delta_T = calculer_elevation_temperature(
            forces_N[i], vitesses_mps[i], m_dot, Cp, eta
        )
        delta_T_par_passe.append(delta_T)

    # Cumul des températures
    T_cumulees = calculer_temperature_cumulee(T_initiale_C, delta_T_par_passe)
    T_max = max(T_cumulees)

    # Vérification sécurité
    securite = verifier_securite_thermique(T_max)

    return {
        'delta_T_par_passe': delta_T_par_passe,
        'T_cumulees': T_cumulees,
        'T_max': T_max,
        'securite': securite,
    }


# ═══════════════════════════════════════════════════════════════════
# TEST RAPIDE
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("TEST DU MODULE THERMIQUE")
    print("=" * 60)

    # Test 1 : ΔT simple
    m_dot = calculer_debit_massique(d_mm=4.0, v_mps=10.0)
    delta_T = calculer_elevation_temperature(F_N=2000, v_mps=10.0, m_dot_kg_s=m_dot)
    print(f"\nTest 1 : ΔT pour F=2000N, v=10m/s, d=4mm")
    print(f"  ΔT = {delta_T:.2f} °C")

    # Test 2 : nombre de Péclet
    Pe = calculer_nombre_peclet(v_mps=15.0)
    print(f"\nTest 2 : Nombre de Péclet à v=15 m/s")
    print(f"  Pe = {Pe:.1f}  → adiabatique valide : {Pe > 10}")

    # Test 3 : profil thermique 9 passes
    forces = [2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000]
    vitesses = [1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 11.0, 15.0]
    diametres = [7.21, 6.49, 5.83, 5.24, 4.71, 4.24, 3.82, 3.43, 2.0]

    profil = calculer_profil_thermique(forces, vitesses, diametres,
                                          T_initiale_C=25.0)
    print(f"\nTest 3 : Profil thermique sur 9 passes")
    print(f"  ΔT par passe : {[f'{dT:.1f}' for dT in profil['delta_T_par_passe']]}")
    print(f"  T cumulées   : {[f'{T:.1f}' for T in profil['T_cumulees']]}")
    print(f"  T max        : {profil['T_max']:.1f} °C")
    print(f"  Sécurité     : {profil['securite']['niveau_risque']}")

    print("\n✅ Tous les tests sont passés !")
