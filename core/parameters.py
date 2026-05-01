"""
═══════════════════════════════════════════════════════════════════════
FICHIER : utils/parameters.py
RÔLE    : Centraliser tous les paramètres physiques et techniques
═══════════════════════════════════════════════════════════════════════

Ce fichier contient TOUS les paramètres utilisés par l'application.
Si vous voulez modifier une valeur par défaut, c'est ici qu'il faut le faire.

Pour les débutants :
- Les "constantes" sont des valeurs qui ne changent JAMAIS
- Les "paramètres par défaut" peuvent être modifiés par l'utilisateur via les sliders
"""

import json
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════
# CONSTANTES PHYSIQUES UNIVERSELLES (ne changent jamais)
# ═══════════════════════════════════════════════════════════════════

R_GAS = 8.314           # Constante des gaz parfaits [J/(mol·K)]
T_REF_KELVIN = 298.15   # Température de référence : 25°C en Kelvin
ZERO_CELSIUS_K = 273.15 # 0°C en Kelvin


# ═══════════════════════════════════════════════════════════════════
# PROPRIÉTÉS DU CUIVRE ETP (Electrolytic Tough Pitch)
# ═══════════════════════════════════════════════════════════════════
# Source : Hosford (2022), Wright (2024), NIST Copper Data

CUIVRE_ETP = {
    # Composition
    'composition': 'Cu >= 99.90%, O 0.02-0.04%',

    # Propriétés mécaniques
    'rho': 8960.0,        # Masse volumique [kg/m³]
    'E': 117e9,           # Module de Young [Pa]
    'nu': 0.34,           # Coefficient de Poisson [-]
    'sigma_y_recuit': 140.0,  # Limite élastique à l'état recuit [MPa]

    # Propriétés thermiques
    'Cp': 385.0,          # Chaleur spécifique [J/(kg·K)]
    'k_thermal': 401.0,   # Conductivité thermique [W/(m·K)]
    'alpha_thermal': 1.16e-4,  # Diffusivité thermique [m²/s]
    'T_fusion': 1356.0,   # Température de fusion [K] (= 1083°C)

    # Propriétés électriques
    'sigma_elec': 58e6,   # Conductivité électrique [S/m] (= 100% IACS)

    # Paramètres de la loi de Hollomon (σ = K·εⁿ)
    'K_hollomon': 335.0,  # Coefficient de résistance [MPa]
    'n_hollomon': 0.50,   # Exposant d'écrouissage [-]

    # Plages de variation acceptables (analyse de sensibilité)
    'K_range': (315.0, 350.0),
    'n_range': (0.44, 0.54),
}


# ═══════════════════════════════════════════════════════════════════
# PARAMÈTRES PAR DÉFAUT DE LA TRÉFILEUSE 9 PASSES (LATRECA)
# ═══════════════════════════════════════════════════════════════════

MACHINE_DEFAULTS = {
    # Géométrie
    'd_0': 8.0,           # Diamètre d'entrée du fil-machine [mm]
    'd_f': 2.0,           # Diamètre de sortie final [mm]
    'n_passes': 9,        # Nombre de passes successives [-]

    # Angles des filières (demi-angle de cône)
    'alpha_default': 6.0, # Angle par défaut [degrés]
    'alpha_min': 4.0,     # Angle minimum acceptable [degrés]
    'alpha_max': 12.0,    # Angle maximum acceptable [degrés]

    # Vitesses
    'v_f_default': 15.0,  # Vitesse de sortie par défaut [m/s]
    'v_min': 5.0,         # Vitesse minimale [m/s]
    'v_max': 30.0,        # Vitesse maximale [m/s]

    # Puissance moteur
    'P_moteur_nominal': 300.0,  # Puissance nominale du moteur [kW]

    # Conditions d'opération
    'T_ambient_C': 25.0,  # Température ambiante atelier [°C]
    'T_shift_h': 8.0,     # Durée d'un poste de travail [heures]
    'eta_OEE': 0.75,      # Taux de rendement synthétique [-]
}


# ═══════════════════════════════════════════════════════════════════
# PARAMÈTRES THERMIQUES (modèle adiabatique de Kim)
# ═══════════════════════════════════════════════════════════════════

THERMAL_PARAMS = {
    'eta_TQ': 0.92,       # Facteur de Taylor-Quinney [-]
                          # (90-95% du travail mécanique → chaleur)

    'T_max_critique_C': 140.0,  # Seuil thermique critique [°C]
                                # Au-delà : destruction du film lubrifiant
}


# ═══════════════════════════════════════════════════════════════════
# PARAMÈTRES DU MODÈLE CTTD (INNOVATION CENTRALE)
# ═══════════════════════════════════════════════════════════════════
# μ(T, t) = μ₀ · f_T(T) · [1 + γ · D(t, T)]
# avec :
#   f_T(T) = exp[β · (T - T_ref) / T_ref]   (facteur thermique d'Arrhenius)
#   D(t,T) = ∫ exp(-Q_lub / (R·T)) dt        (dégradation cumulée)

CTTD_DEFAULTS = {
    'mu_critique_factor': 1.5,  # Le lubrifiant est "mort" quand μ atteint
                                # 1.5 × μ_initial (Wakiru et al., 2019)
}


# ═══════════════════════════════════════════════════════════════════
# CONTRAINTES DE SÉCURITÉ INDUSTRIELLE
# ═══════════════════════════════════════════════════════════════════

SAFETY_CONSTRAINTS = {
    # C1 : Sécurité mécanique
    # σ_tréfilage / σ_y ≤ 0.6 → marge de sécurité de 40 % contre la rupture
    'sigma_safety_factor': 0.6,

    # C2 : Sécurité thermique
    # T cumulée ≤ 140°C → protection du lubrifiant
    'T_max_C': 140.0,

    # C3 : Capacité moteur
    # ΣP_passes ≤ P_nominale_moteur
    # (déjà défini dans MACHINE_DEFAULTS)

    # C4 : Intégrité tribologique (NOUVELLE - liée à CTTD)
    # μ(T_max, t_max) ≤ μ_critique
    'mu_critique_factor': 1.5,
}


# ═══════════════════════════════════════════════════════════════════
# PARAMÈTRES NSGA-II (algorithme génétique)
# ═══════════════════════════════════════════════════════════════════

NSGA2_PARAMS = {
    'pop_size': 100,      # Taille de la population [individus]
    'n_generations': 200, # Nombre de générations
    'p_crossover': 0.9,   # Probabilité de croisement
    'eta_crossover': 15,  # Distribution index pour SBX crossover
    'eta_mutation': 20,   # Distribution index pour mutation polynomiale
    'convergence_window': 20,   # Fenêtre de stabilité d'arrêt
    'convergence_tol': 0.01,    # Tolérance (1 %)
}


# ═══════════════════════════════════════════════════════════════════
# CHARGEMENT DES DONNÉES JSON
# ═══════════════════════════════════════════════════════════════════

DATA_DIR = Path(__file__).parent.parent / "data"


def load_lubricants_database():
    """
    Charge la base de données des 4 lubrifiants depuis data/lubricants.json.

    Returns
    -------
    dict
        Dictionnaire des lubrifiants avec leurs paramètres CTTD.
    """
    file_path = DATA_DIR / "lubricants.json"
    if not file_path.exists():
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_latreca_baseline():
    """
    Charge les paramètres LATRECA actuels (à compléter après visite).

    Returns
    -------
    dict
        Paramètres machine actuels mesurés à LATRECA.
    """
    file_path = DATA_DIR / "latreca_baseline.json"
    if not file_path.exists():
        return MACHINE_DEFAULTS.copy()
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_constructor_baseline():
    """
    Charge les paramètres nominaux du constructeur.

    Returns
    -------
    dict
        Paramètres machine selon spécifications constructeur.
    """
    file_path = DATA_DIR / "constructor_baseline.json"
    if not file_path.exists():
        return MACHINE_DEFAULTS.copy()
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_all_default_params():
    """
    Retourne TOUS les paramètres par défaut dans un seul dictionnaire.

    Très pratique pour initialiser les calculs.
    """
    params = {}
    params.update(CUIVRE_ETP)
    params.update(MACHINE_DEFAULTS)
    params.update(THERMAL_PARAMS)
    params.update(CTTD_DEFAULTS)
    return params


# ═══════════════════════════════════════════════════════════════════
# CONVERSIONS UTILES
# ═══════════════════════════════════════════════════════════════════

def celsius_to_kelvin(T_C):
    """Convertit Celsius → Kelvin."""
    return T_C + ZERO_CELSIUS_K


def kelvin_to_celsius(T_K):
    """Convertit Kelvin → Celsius."""
    return T_K - ZERO_CELSIUS_K


def degrees_to_radians(angle_deg):
    """Convertit degrés → radians."""
    import math
    return angle_deg * math.pi / 180.0
