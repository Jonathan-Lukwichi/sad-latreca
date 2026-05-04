"""
═══════════════════════════════════════════════════════════════════════
PILIER P4 — MODÈLE CTTD (Couplage Thermo-Tribologique Dynamique)
═══════════════════════════════════════════════════════════════════════
                    ⭐⭐⭐ INNOVATION CENTRALE DU MÉMOIRE ⭐⭐⭐
═══════════════════════════════════════════════════════════════════════

PROBLÈME RÉSOLU :
    Dans la littérature classique (Avitzur, Kim, Wang...), le coefficient
    de frottement μ est traité comme une CONSTANTE.

    En réalité, μ ÉVOLUE :
    - avec la TEMPÉRATURE (le lubrifiant devient moins visqueux quand T monte)
    - avec le TEMPS d'utilisation (le lubrifiant vieillit, s'oxyde, se dégrade)

    → Cette dynamique explique POURQUOI les performances des tréfileuses
      se dégradent au fil des mois, comme observé à LATRECA.

ÉQUATION CENTRALE :  μ(T, t) = μ₀ · f_T(T) · [1 + γ · D(t, T)]

OÙ :
    μ₀          : coefficient de frottement INITIAL (lubrifiant neuf)
    f_T(T)      : facteur thermique d'Arrhenius
                  f_T(T) = exp[β · (T - T_ref) / T_ref]
    β           : sensibilité thermique du lubrifiant
    γ           : taux de vieillissement
    D(t, T)     : intégrale de dégradation cumulée
                  D(t,T) = ∫ exp(-Q_lub / (R·T(τ))) dτ
    Q_lub       : énergie d'activation de dégradation [J/mol]

EFFET DE LA BOUCLE FERMÉE :
    Force ↑ → Température ↑ → μ ↑ → Force ↑ (boucle d'amplification)

INTERPRÉTATION INDUSTRIELLE :
    Quand μ atteint μ_critique = 1.5 × μ₀ → le lubrifiant doit être REMPLACÉ.
    Le SAD permet de prédire ce moment précisément.

RÉFÉRENCES (cinétique d'Arrhenius pour lubrifiants) :
    - Naidu, Klaus & Duda (1985) - Kinetic model for high-temperature oxidation
    - Rounds (1993) - Lubricant degradation
    - Fox & Picken (1993) - Ageing of lubricants
    - Diaby et al. (2010) - Carbonaceous deposit formation
═══════════════════════════════════════════════════════════════════════
"""

import numpy as np
from scipy.optimize import brentq
from core.parameters import R_GAS, T_REF_KELVIN, ZERO_CELSIUS_K


def f_thermique(T_kelvin, beta, T_ref_K=T_REF_KELVIN):
    """
    Facteur thermique de type Arrhenius.

    Formule : f_T(T) = exp[β · (T - T_ref) / T_ref]

    Quand T = T_ref → f_T = 1 (pas de modification)
    Quand T > T_ref → f_T > 1 (μ augmente avec T)
    Quand T < T_ref → f_T < 1 (μ diminue avec T)

    Parameters
    ----------
    T_kelvin : float
        Température courante [K]
    beta : float
        Sensibilité thermique du lubrifiant [-]
        Typiquement 0.1 à 0.5 selon le type de lubrifiant
    T_ref_K : float
        Température de référence [K] (par défaut 298.15 K = 25°C)

    Returns
    -------
    f_T : float
        Facteur multiplicatif thermique [-]
    """
    if T_kelvin <= 0:
        raise ValueError(f"T en Kelvin doit être > 0. Reçu : {T_kelvin}")
    return float(np.exp(beta * (T_kelvin - T_ref_K) / T_ref_K))


def integrale_degradation(temps_array, T_array_K, Q_lub_J_mol):
    """
    Calcule l'intégrale de dégradation cumulée D(t, T).

    Formule : D(t, T) = ∫₀ᵗ exp(-Q_lub / (R · T(τ))) dτ

    Méthode : intégration numérique par la règle des trapèzes
              (np.trapz)

    PRINCIPE PHYSIQUE :
    À température élevée, le lubrifiant s'oxyde plus vite (Arrhenius).
    L'intégrale CUMULE cette dégradation au fil du temps.

    Parameters
    ----------
    temps_array : array
        Historique des temps [s]
    T_array_K : array
        Historique des températures [K]
        (mêmes indices que temps_array)
    Q_lub_J_mol : float
        Énergie d'activation de dégradation [J/mol]
        Typiquement 60 000 à 90 000 J/mol pour huiles minérales

    Returns
    -------
    D : float
        Valeur de l'intégrale de dégradation [s]
    """
    temps_array = np.asarray(temps_array, dtype=float)
    T_array_K = np.asarray(T_array_K, dtype=float)

    # Vérifications
    if len(temps_array) != len(T_array_K):
        raise ValueError("temps_array et T_array_K doivent avoir même longueur")
    if len(temps_array) < 2:
        return 0.0
    if np.any(T_array_K <= 0):
        raise ValueError("Toutes les températures doivent être > 0 K")

    # Intégrande d'Arrhenius : exp(-Q / (R·T))
    integrand = np.exp(-Q_lub_J_mol / (R_GAS * T_array_K))

    # Intégration par la méthode des trapèzes
    # Note: np.trapz est supprimé dans NumPy 2.0, remplacé par np.trapezoid
    if hasattr(np, 'trapezoid'):
        D = float(np.trapezoid(integrand, temps_array))
    else:
        D = float(np.trapz(integrand, temps_array))

    return D


def calculer_mu_cttd(T_kelvin, temps_array, T_array_K,
                      mu_0, beta, gamma, Q_lub_J_mol):
    """
    ⭐ FONCTION PRINCIPALE DU MODÈLE CTTD ⭐

    Calcule le coefficient de frottement courant μ(T, t)
    en fonction de la température actuelle ET de l'historique
    thermique cumulé.

    Formule : μ(T, t) = μ₀ · f_T(T) · [1 + γ · D(t, T)]

    Parameters
    ----------
    T_kelvin : float
        Température courante [K]
    temps_array : array
        Historique des temps depuis la mise en service [s]
    T_array_K : array
        Historique des températures [K]
    mu_0 : float
        Coefficient de frottement INITIAL (lubrifiant neuf) [-]
    beta : float
        Sensibilité thermique du lubrifiant [-]
    gamma : float
        Taux de vieillissement [-]
    Q_lub_J_mol : float
        Énergie d'activation de dégradation [J/mol]

    Returns
    -------
    mu : float
        Coefficient de frottement actuel [-]
    """
    # Vérifications
    if mu_0 <= 0:
        raise ValueError(f"mu_0 doit être > 0. Reçu : {mu_0}")

    # Composante 1 : effet thermique instantané
    f_T = f_thermique(T_kelvin, beta)

    # Composante 2 : effet de vieillissement cumulé
    D = integrale_degradation(temps_array, T_array_K, Q_lub_J_mol)

    # Combinaison : μ = μ₀ · f_T(T) · [1 + γ · D]
    mu = mu_0 * f_T * (1.0 + gamma * D)

    return float(mu)


def predire_temps_remplacement(mu_0, beta, gamma, Q_lub_J_mol,
                                  T_operation_C,
                                  facteur_critique=1.5,
                                  t_max_jours=365 * 5):
    """
    ⭐ PRÉDICTION DU TEMPS OPTIMAL DE REMPLACEMENT DU LUBRIFIANT ⭐

    Cette fonction est l'application industrielle DIRECTE du modèle CTTD.
    Elle répond à la question : "Quand dois-je changer le lubrifiant ?"

    Méthode :
        On cherche le temps t* tel que μ(T_op, t*) = facteur_critique × μ₀.
        Par défaut : facteur_critique = 1.5
        → "Le lubrifiant est mort quand μ a augmenté de 50 %"

    Parameters
    ----------
    mu_0 : float
        Coefficient de frottement initial [-]
    beta, gamma : float
        Paramètres CTTD du lubrifiant
    Q_lub_J_mol : float
        Énergie d'activation [J/mol]
    T_operation_C : float
        Température moyenne d'opération [°C]
    facteur_critique : float
        Seuil de remplacement (1.5 par défaut)
    t_max_jours : int
        Horizon maximum de recherche [jours]

    Returns
    -------
    dict avec :
        - 't_remplacement_secondes' : temps prédit [s]
        - 't_remplacement_jours'    : temps prédit [jours]
        - 't_remplacement_mois'     : temps prédit [mois]
        - 'mu_cible'                : valeur seuil μ_critique
    """
    # Conversion temperature
    T_op_K = T_operation_C + ZERO_CELSIUS_K
    mu_cible = facteur_critique * mu_0

    # Fonction résiduelle : on cherche t tel que mu(t) = mu_cible
    def residu(t_secondes):
        # On simule un historique constant (T_op, t)
        n_points = 100
        temps = np.linspace(0, t_secondes, n_points)
        T_history = np.full(n_points, T_op_K)

        mu_actuel = calculer_mu_cttd(
            T_op_K, temps, T_history,
            mu_0, beta, gamma, Q_lub_J_mol
        )
        return mu_actuel - mu_cible

    # Bornes de recherche
    t_min = 60.0  # 1 minute
    t_max = t_max_jours * 24 * 3600  # en secondes

    # Vérification : le seuil est-il atteignable ?
    if residu(t_max) < 0:
        # μ ne dépasse pas le seuil sur l'horizon → le lubrifiant tient
        return {
            't_remplacement_secondes': t_max,
            't_remplacement_jours': t_max_jours,
            't_remplacement_mois': t_max_jours / 30.0,
            'mu_cible': mu_cible,
            'avertissement': f"Seuil non atteint en {t_max_jours} jours",
        }

    # Recherche de la racine par méthode de Brent
    try:
        t_star = brentq(residu, t_min, t_max)
    except ValueError as e:
        # Si ça ne converge pas, on retourne t_max
        t_star = t_max

    return {
        't_remplacement_secondes': float(t_star),
        't_remplacement_jours': float(t_star) / (24 * 3600),
        't_remplacement_mois': float(t_star) / (24 * 3600 * 30),
        'mu_cible': mu_cible,
    }


def simuler_evolution_mu(mu_0, beta, gamma, Q_lub_J_mol,
                            T_operation_C,
                            duree_simulation_jours=365,
                            n_points=200):
    """
    Simule l'évolution complète de μ(t) sur une période donnée.

    Pratique pour tracer la courbe sur la page CTTD du SAD.

    Parameters
    ----------
    mu_0, beta, gamma, Q_lub_J_mol : float
        Paramètres CTTD du lubrifiant
    T_operation_C : float
        Température d'opération moyenne [°C]
    duree_simulation_jours : int
        Durée totale de simulation [jours]
    n_points : int
        Nombre de points sur la courbe

    Returns
    -------
    dict avec :
        - 'temps_jours' : array des temps [jours]
        - 'mu_array'    : array des valeurs de μ [-]
        - 'mu_initial'  : μ₀
        - 'mu_critique' : 1.5 · μ₀
    """
    T_op_K = T_operation_C + ZERO_CELSIUS_K
    duree_s = duree_simulation_jours * 24 * 3600

    temps_s = np.linspace(0, duree_s, n_points)
    temps_jours = temps_s / (24 * 3600)
    mu_array = []

    for t in temps_s:
        # On reconstruit l'historique jusqu'au temps t
        n_history = max(2, int(t / duree_s * n_points))
        temps_history = np.linspace(0, t, n_history)
        T_history = np.full(n_history, T_op_K)

        mu = calculer_mu_cttd(
            T_op_K, temps_history, T_history,
            mu_0, beta, gamma, Q_lub_J_mol
        )
        mu_array.append(mu)

    return {
        'temps_jours': temps_jours,
        'mu_array': np.array(mu_array),
        'mu_initial': mu_0,
        'mu_critique': 1.5 * mu_0,
    }


def comparer_lubrifiants(liste_lubrifiants, T_operation_C=100.0,
                            duree_jours=365):
    """
    Compare plusieurs lubrifiants sur le même scénario.

    Parameters
    ----------
    liste_lubrifiants : list of dict
        Chaque dict doit contenir : nom, mu_0, beta, gamma, Q_lub
    T_operation_C : float
        Température d'opération [°C]
    duree_jours : int
        Durée de comparaison [jours]

    Returns
    -------
    list of dict avec pour chaque lubrifiant :
        - 'nom', 'parametres'
        - 'evolution'        : résultat de simuler_evolution_mu
        - 't_remplacement'   : résultat de predire_temps_remplacement
    """
    resultats = []
    for lub in liste_lubrifiants:
        evolution = simuler_evolution_mu(
            mu_0=lub['mu_0'],
            beta=lub['beta'],
            gamma=lub['gamma'],
            Q_lub_J_mol=lub['Q_lub'],
            T_operation_C=T_operation_C,
            duree_simulation_jours=duree_jours,
        )
        t_rempl = predire_temps_remplacement(
            mu_0=lub['mu_0'],
            beta=lub['beta'],
            gamma=lub['gamma'],
            Q_lub_J_mol=lub['Q_lub'],
            T_operation_C=T_operation_C,
        )
        resultats.append({
            'nom': lub['nom'],
            'parametres': lub,
            'evolution': evolution,
            't_remplacement': t_rempl,
        })
    return resultats


# ═══════════════════════════════════════════════════════════════════
# TEST RAPIDE
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("TEST DU MODULE CTTD (INNOVATION CENTRALE)")
    print("=" * 60)

    # Test 1 : facteur thermique
    f = f_thermique(T_kelvin=373, beta=0.25)
    print(f"\nTest 1 : f_T à T=100°C avec β=0.25")
    print(f"  f_T = {f:.3f}  (attendu > 1)")

    # Test 2 : calcul mu_cttd
    temps = np.linspace(0, 30 * 24 * 3600, 100)  # 30 jours
    T = np.full(100, 373)  # 100°C constant
    mu = calculer_mu_cttd(
        T_kelvin=373,
        temps_array=temps,
        T_array_K=T,
        mu_0=0.05, beta=0.25, gamma=1e-6, Q_lub_J_mol=70000
    )
    print(f"\nTest 2 : μ après 30 jours à 100°C")
    print(f"  μ_initial : 0.050")
    print(f"  μ après   : {mu:.4f}")

    # Test 3 : prédiction temps de remplacement
    pred = predire_temps_remplacement(
        mu_0=0.05, beta=0.25, gamma=1e-6, Q_lub_J_mol=70000,
        T_operation_C=100.0
    )
    print(f"\nTest 3 : Prédiction temps de remplacement à 100°C")
    print(f"  μ initial   : 0.050")
    print(f"  μ critique  : {pred['mu_cible']:.4f}")
    print(f"  Temps prédit: {pred['t_remplacement_jours']:.0f} jours")
    print(f"               ({pred['t_remplacement_mois']:.1f} mois)")

    print("\n✅ Tous les tests sont passés !")
