"""
═══════════════════════════════════════════════════════════════════════
SOLVEUR COUPLÉ — BOUCLE THERMO-TRIBOLOGIQUE
═══════════════════════════════════════════════════════════════════════

Ce module ASSEMBLE les 4 piliers scientifiques :
    P1 - Hollomon (modèle d'écrouissage)
    P2 - Avitzur  (mécanique du tréfilage)
    P3 - Kim      (thermique adiabatique)
    P4 - CTTD     (couplage thermo-tribologique dynamique)

ALGORITHME GÉNÉRAL :
    Pour chaque passe i = 1, 2, ..., 9 :
        1. Calculer ε_i et σ_bar_i  (Hollomon)
        2. Calculer F_i              (Avitzur avec μ courant)
        3. Calculer ΔT_i             (Kim)
        4. Mettre à jour T_total
        5. Mettre à jour μ           (CTTD avec nouvelle T)

    Renvoyer toutes les grandeurs calculées + KPIs (Z1, Z2)

UTILISATION :
    Cette fonction est appelée :
    - À chaque scénario simulé par l'utilisateur dans le SAD
    - À chaque évaluation de NSGA-II pendant l'optimisation
═══════════════════════════════════════════════════════════════════════
"""

import math
import numpy as np

# Import des modules des piliers
from core.hollomon import (
    calculer_sequence_passes,
    calculer_deformation_cumulee,
    calculer_contrainte_hollomon,
    calculer_contrainte_moyenne_passe,
)
from core.avitzur import calculer_force_avitzur, calculer_section
from core.thermal import (
    calculer_debit_massique,
    calculer_elevation_temperature,
    calculer_temperature_cumulee,
    verifier_securite_thermique,
)
from core.cttd import calculer_mu_cttd
from core.parameters import (
    CUIVRE_ETP, MACHINE_DEFAULTS, THERMAL_PARAMS,
    SAFETY_CONSTRAINTS, ZERO_CELSIUS_K,
)


def calculer_vitesses_par_passe(v_f, diametres, n_passes):
    """
    Calcule la vitesse du fil dans chaque passe.

    PRINCIPE : conservation du débit massique en régime stationnaire
        ρ · A_i · v_i = ρ · A_f · v_f
        → v_i = v_f · (A_f / A_i)

    Parameters
    ----------
    v_f : float
        Vitesse du fil en sortie (dernière passe) [m/s]
    diametres : list
        Liste des diamètres après chaque passe [mm]
    n_passes : int
        Nombre de passes

    Returns
    -------
    list
        Vitesses dans chaque passe [m/s]
        v_i = v_f * (d_f / d_i)²
    """
    d_f = diametres[-1]
    A_f = math.pi * (d_f / 1000)**2 / 4

    vitesses = []
    for i in range(1, n_passes + 1):
        d_i = diametres[i]
        A_i = math.pi * (d_i / 1000)**2 / 4
        v_i = v_f * A_f / A_i
        vitesses.append(v_i)
    return vitesses


def simuler_scenario(parametres):
    """
    ⭐ FONCTION PRINCIPALE : simule un scénario complet de tréfilage.

    Cette fonction est le CŒUR du SAD : elle exécute la chaîne de calcul
    complète sur les 9 passes en couplant tous les piliers scientifiques.

    Parameters
    ----------
    parametres : dict
        Dictionnaire contenant TOUS les paramètres :
        - Matériau : K, n, rho, Cp
        - Machine : d_0, d_f, n_passes, alphas, v_f
        - Lubrifiant : mu_0, beta, gamma, Q_lub
        - Conditions : T_ambient_C, eta_TQ
        - (Optionnel) historique pour CTTD : t_history_s, T_history_K
        - (Optionnel) jours d'utilisation : age_lubrifiant_jours

    Returns
    -------
    dict avec :
        - 'diametres'           : list des diamètres [mm]
        - 'vitesses'            : list des vitesses par passe [m/s]
        - 'deformations'        : list des ε cumulées [-]
        - 'contraintes_y'       : list des σ_y actualisées [MPa]
        - 'contraintes_moyennes': list des σ̄ par passe [MPa]
        - 'forces'              : list des F par passe [N]
        - 'puissances'          : list des P par passe [W]
        - 'temperatures'        : list des T cumulées [°C]
        - 'delta_T'             : list des ΔT par passe [°C]
        - 'mu_par_passe'        : list des μ utilisés par passe [-]
        - 'KPIs'                : dict des KPIs (Z1, Z2, marges, ...)
        - 'securite'            : dict des vérifications de sécurité
    """
    # ─── Defense en profondeur : Store peut etre None ou contenir des Nones ───
    parametres = parametres or {}

    def _f(key, default):
        v = parametres.get(key)
        try:
            return float(v) if v is not None else float(default)
        except (TypeError, ValueError):
            return float(default)

    def _i(key, default):
        v = parametres.get(key)
        try:
            return int(v) if v is not None else int(default)
        except (TypeError, ValueError):
            return int(default)

    # ─── Extraction des paramètres ───
    K = _f('K', CUIVRE_ETP['K_hollomon'])
    n = _f('n', CUIVRE_ETP['n_hollomon'])
    rho = _f('rho', CUIVRE_ETP['rho'])
    Cp = _f('Cp', CUIVRE_ETP['Cp'])

    d_0 = _f('d_0', MACHINE_DEFAULTS['d_0'])
    d_f = _f('d_f', MACHINE_DEFAULTS['d_f'])
    n_passes = max(1, _i('n_passes', MACHINE_DEFAULTS['n_passes']))
    v_f = _f('v_f', MACHINE_DEFAULTS['v_f_default'])

    # Validation geometrique : d_0 doit > d_f
    if d_0 <= d_f:
        raise ValueError(
            f"Configuration géométrique invalide : "
            f"diamètre d'entrée ({d_0:.2f} mm) doit être supérieur "
            f"au diamètre de sortie ({d_f:.2f} mm)."
        )

    alphas_raw = parametres.get('alphas')
    if not isinstance(alphas_raw, (list, tuple)) or len(alphas_raw) != n_passes:
        alphas = [MACHINE_DEFAULTS['alpha_default']] * n_passes
    else:
        alphas = [float(a) if a is not None else MACHINE_DEFAULTS['alpha_default']
                  for a in alphas_raw]

    mu_0 = max(1e-4, _f('mu_0', 0.05))
    beta = _f('beta', 0.25)
    gamma = _f('gamma', 1e-6)
    Q_lub = _f('Q_lub', 70000.0)

    T_ambient = _f('T_ambient_C', MACHINE_DEFAULTS['T_ambient_C'])
    eta_TQ = _f('eta_TQ', THERMAL_PARAMS['eta_TQ'])
    age_lubrifiant_jours = _f('age_lubrifiant_jours', 0)

    T_shift = _f('T_shift_h', MACHINE_DEFAULTS['T_shift_h'])
    eta_OEE = _f('eta_OEE', MACHINE_DEFAULTS['eta_OEE'])
    P_moteur_nominal = _f('P_moteur_nominal',
                           MACHINE_DEFAULTS['P_moteur_nominal'])

    # ─── Calculs préalables ───

    # 1. Diamètres successifs
    diametres = calculer_sequence_passes(d_0, d_f, n_passes)

    # 2. Vitesses par passe (conservation du débit)
    vitesses = calculer_vitesses_par_passe(v_f, diametres, n_passes)

    # 3. Déformations cumulées
    deformations = [0.0]
    for i in range(1, n_passes + 1):
        eps = calculer_deformation_cumulee(d_0, diametres[i])
        deformations.append(eps)

    # 4. Contraintes σ_y et σ̄
    contraintes_y = [0.0]
    contraintes_moyennes = []
    for i in range(1, n_passes + 1):
        sigma_y = calculer_contrainte_hollomon(deformations[i], K, n)
        contraintes_y.append(sigma_y)
        sigma_moy = calculer_contrainte_moyenne_passe(
            deformations[i - 1], deformations[i], K, n
        )
        contraintes_moyennes.append(sigma_moy)

    # ─── BOUCLE THERMO-TRIBOLOGIQUE COUPLÉE ───

    forces = []
    puissances = []
    delta_T_list = []
    T_cumulees = [T_ambient]
    mu_par_passe = []
    sigma_d_list = []

    # Historique pour CTTD (initial = âge du lubrifiant)
    t_history = [age_lubrifiant_jours * 24 * 3600]
    T_history_K = [T_ambient + ZERO_CELSIUS_K]

    T_actuelle = T_ambient

    for i in range(n_passes):
        # ─── Étape 1 : Calculer μ courant via CTTD ───
        T_K = T_actuelle + ZERO_CELSIUS_K
        if len(t_history) >= 2:
            mu_courant = calculer_mu_cttd(
                T_K, t_history, T_history_K,
                mu_0, beta, gamma, Q_lub
            )
        else:
            mu_courant = mu_0  # premier calcul

        mu_par_passe.append(mu_courant)

        # ─── Étape 2 : Calculer la force par Avitzur ───
        resultat_avitzur = calculer_force_avitzur(
            sigma_bar_MPa=contraintes_moyennes[i],
            d_in_mm=diametres[i],
            d_out_mm=diametres[i + 1],
            mu=mu_courant,
            alpha_deg=alphas[i]
        )
        F = resultat_avitzur['F_total']
        forces.append(F)
        sigma_d_list.append(resultat_avitzur['sigma_d_MPa'])

        # ─── Étape 3 : Calculer la puissance ───
        P = F * vitesses[i]
        puissances.append(P)

        # ─── Étape 4 : Calculer ΔT ───
        m_dot = calculer_debit_massique(diametres[i + 1], vitesses[i], rho)
        delta_T = calculer_elevation_temperature(
            F, vitesses[i], m_dot, Cp, eta_TQ
        )
        delta_T_list.append(delta_T)

        # ─── Étape 5 : Mettre à jour T cumulée ───
        T_actuelle += delta_T
        T_cumulees.append(T_actuelle)

        # ─── Étape 6 : Mettre à jour l'historique pour CTTD ───
        # On suppose que chaque passe dure ~1 seconde (pour un fil long)
        t_history.append(t_history[-1] + 1.0)
        T_history_K.append(T_actuelle + ZERO_CELSIUS_K)

    # ─── Calcul des KPIs ───

    # KPI Z1 : Production journalière [tonnes/jour]
    # Z1 = ρ · (π·d_f²/4) · v_f · 3600 · T_shift · η_OEE
    A_f = calculer_section(d_f)
    debit_volumique_m3_s = A_f * v_f
    debit_massique_kg_s = rho * debit_volumique_m3_s
    Z1_kg_jour = debit_massique_kg_s * 3600 * T_shift * eta_OEE
    Z1_tonnes_jour = Z1_kg_jour / 1000.0

    # KPI Z2 : SEC (Specific Energy Consumption) [kWh/tonne]
    # Z2 = somme(F_i · v_i) / debit_massique
    P_totale_W = sum(puissances)
    if debit_massique_kg_s > 0:
        SEC_J_kg = P_totale_W / debit_massique_kg_s
        Z2_kWh_tonne = SEC_J_kg / 3600.0  # J/kg → kWh/tonne (×1000/3.6e6)
    else:
        Z2_kWh_tonne = 0.0

    # ─── Vérifications de sécurité ───

    # C1 : Sécurité mécanique (toutes passes)
    securite_C1 = []
    for i in range(n_passes):
        if contraintes_y[i + 1] > 0:
            ratio = sigma_d_list[i] / contraintes_y[i + 1]
        else:
            ratio = 0.0
        securite_C1.append({
            'passe': i + 1,
            'ratio': ratio,
            'ok': ratio <= SAFETY_CONSTRAINTS['sigma_safety_factor'],
        })
    marge_mecanique_min = min(
        [SAFETY_CONSTRAINTS['sigma_safety_factor'] - s['ratio']
         for s in securite_C1]
    )

    # C2 : Sécurité thermique
    securite_C2 = verifier_securite_thermique(max(T_cumulees))

    # C3 : Capacité moteur
    P_totale_kW = P_totale_W / 1000.0
    securite_C3 = {
        'P_total_kW': P_totale_kW,
        'P_nominale_kW': P_moteur_nominal,
        'ratio': P_totale_kW / P_moteur_nominal if P_moteur_nominal > 0 else 0,
        'ok': P_totale_kW <= P_moteur_nominal,
    }

    # C4 : Intégrité tribologique
    mu_max = max(mu_par_passe)
    securite_C4 = {
        'mu_actuel': mu_max,
        'mu_critique': SAFETY_CONSTRAINTS['mu_critique_factor'] * mu_0,
        'ok': mu_max <= SAFETY_CONSTRAINTS['mu_critique_factor'] * mu_0,
    }

    # ─── Assemblage du résultat ───
    return {
        'diametres': diametres,
        'vitesses': vitesses,
        'deformations': deformations,
        'contraintes_y': contraintes_y,
        'contraintes_moyennes': contraintes_moyennes,
        'sigma_d': sigma_d_list,
        'forces': forces,
        'puissances': puissances,
        'temperatures': T_cumulees,
        'delta_T': delta_T_list,
        'mu_par_passe': mu_par_passe,
        'KPIs': {
            'Z1_production_t_jour': Z1_tonnes_jour,
            'Z2_SEC_kWh_tonne': Z2_kWh_tonne,
            'P_totale_kW': P_totale_kW,
            'T_max_C': max(T_cumulees),
            'F_max_N': max(forces),
            'mu_max': mu_max,
            'marge_mecanique_pourcent': marge_mecanique_min * 100 / SAFETY_CONSTRAINTS['sigma_safety_factor'],
            'marge_thermique_C': securite_C2['marge_C'],
        },
        'securite': {
            'C1_mecanique': {
                'ok': all(s['ok'] for s in securite_C1),
                'detail': securite_C1,
                'marge_min': marge_mecanique_min,
            },
            'C2_thermique': securite_C2,
            'C3_moteur': securite_C3,
            'C4_tribologique': securite_C4,
            'tout_ok': (
                all(s['ok'] for s in securite_C1) and
                securite_C2['securite_ok'] and
                securite_C3['ok'] and
                securite_C4['ok']
            ),
        },
    }


# ═══════════════════════════════════════════════════════════════════
# TEST RAPIDE
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("TEST DU SOLVEUR COUPLÉ (chaîne complète)")
    print("=" * 60)

    # Scénario LATRECA baseline
    parametres = {
        'K': 335.0,
        'n': 0.50,
        'd_0': 8.0,
        'd_f': 2.0,
        'n_passes': 9,
        'v_f': 15.0,
        'alphas': [6.0] * 9,
        'mu_0': 0.05,
        'beta': 0.25,
        'gamma': 1e-6,
        'Q_lub': 70000.0,
        'T_ambient_C': 25.0,
        'age_lubrifiant_jours': 30,
    }

    resultat = simuler_scenario(parametres)

    print(f"\n--- RÉSULTATS ---")
    print(f"Diamètres        : {[f'{d:.2f}' for d in resultat['diametres']]}")
    print(f"Vitesses (m/s)   : {[f'{v:.2f}' for v in resultat['vitesses']]}")
    print(f"Forces (N)       : {[f'{F:.0f}' for F in resultat['forces']]}")
    print(f"ΔT par passe (°C): {[f'{t:.1f}' for t in resultat['delta_T']]}")
    print(f"T cumulée (°C)   : {[f'{t:.1f}' for t in resultat['temperatures']]}")
    print(f"μ par passe      : {[f'{m:.4f}' for m in resultat['mu_par_passe']]}")

    print(f"\n--- KPIs ---")
    for k, v in resultat['KPIs'].items():
        print(f"  {k:30s}: {v:.2f}")

    print(f"\n--- SÉCURITÉ ---")
    print(f"  C1 Mécanique : {'✓' if resultat['securite']['C1_mecanique']['ok'] else '✗'}")
    print(f"  C2 Thermique : {'✓' if resultat['securite']['C2_thermique']['securite_ok'] else '✗'}")
    print(f"  C3 Moteur    : {'✓' if resultat['securite']['C3_moteur']['ok'] else '✗'}")
    print(f"  C4 Tribo     : {'✓' if resultat['securite']['C4_tribologique']['ok'] else '✗'}")
    print(f"  TOUT OK      : {'✅' if resultat['securite']['tout_ok'] else '❌'}")
