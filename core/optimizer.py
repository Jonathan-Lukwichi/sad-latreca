"""
═══════════════════════════════════════════════════════════════════════
PILIER P5 — ALGORITHME NSGA-II (Deb et al., 2002)
═══════════════════════════════════════════════════════════════════════

PRINCIPE :
    NSGA-II = Non-dominated Sorting Genetic Algorithm II
    C'est un algorithme génétique qui résout un problème
    d'optimisation à PLUSIEURS objectifs CONTRADICTOIRES.

NOTRE PROBLÈME :
    Variables de décision (X) : 11 paramètres à optimiser
        - v_f       : vitesse de sortie [m/s]
        - mu_0      : coefficient de frottement initial [-]
        - alpha_1..alpha_9 : 9 angles de filière [°]

    Fonctions objectifs (à optimiser simultanément) :
        - Maximiser  Z1 = production journalière [tonnes/jour]
        - Minimiser  Z2 = consommation énergétique [kWh/tonne]

    Contraintes (à respecter) :
        - C1 : sécurité mécanique  (σ_d ≤ 0.6 · σ_y)
        - C2 : sécurité thermique  (T ≤ 140°C)
        - C3 : capacité moteur     (P ≤ P_nominal)
        - C4 : intégrité tribologique (μ ≤ 1.5 · μ_0)

RÉSULTAT :
    NSGA-II produit un FRONT DE PARETO :
    → un ensemble de solutions non-dominées
    → chaque solution représente un compromis Z1/Z2
    → l'utilisateur choisit son point de fonctionnement

RÉFÉRENCES :
    Deb, K. et al. (2002). NSGA-II. IEEE TEC, 6(2), 182-197.
    Blank, J. & Deb, K. (2020). pymoo. IEEE Access, 8, 89497-89509.
═══════════════════════════════════════════════════════════════════════
"""

import numpy as np

from core.coupled_solver import simuler_scenario
from core.parameters import (
    MACHINE_DEFAULTS, NSGA2_PARAMS, SAFETY_CONSTRAINTS, CUIVRE_ETP,
)


# Import pymoo en lazy : l'optimisation est seulement demarree a la demande.
# Si le package est absent, on l'indique clairement a l'utilisateur.
try:
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.core.problem import ElementwiseProblem
    from pymoo.core.callback import Callback
    from pymoo.optimize import minimize
    from pymoo.operators.crossover.sbx import SBX
    from pymoo.operators.mutation.pm import PM
    from pymoo.termination import get_termination
    PYMOO_AVAILABLE = True
    PYMOO_ERROR = None
except ImportError as e:
    PYMOO_AVAILABLE = False
    PYMOO_ERROR = str(e)
    # Stub minimal pour que la classe ProblemeTrefilage puisse etre importee
    class ElementwiseProblem:
        def __init__(self, *args, **kwargs): pass

    class Callback:
        def __init__(self, *args, **kwargs):
            self.data = {}


class HistoryCallback(Callback):
    """
    Capture les metriques d'evolution generation par generation pour
    afficher la convergence de l'algorithme dans l'UI.

    Pour chaque generation, on stocke :
        - best_Z1   : meilleure production realisable (max parmi les feasibles)
        - best_Z2   : meilleure SEC realisable (min parmi les feasibles)
        - mean_Z1, mean_Z2 : moyennes sur la population
        - n_feasible : nombre d'individus respectant toutes les contraintes
        - n_pareto   : taille du front non-domine courant
    """

    def __init__(self):
        super().__init__()
        self.data["generation"] = []
        self.data["best_Z1"] = []
        self.data["best_Z2"] = []
        self.data["mean_Z1"] = []
        self.data["mean_Z2"] = []
        self.data["n_feasible"] = []
        self.data["n_pareto"] = []

    def notify(self, algorithm):
        gen = int(algorithm.n_gen)
        F = algorithm.pop.get("F")  # objectifs : [-Z1, Z2]
        G = algorithm.pop.get("G")  # contraintes (≤ 0 = feasible)

        # Indices feasibles (toutes contraintes G_i ≤ 0)
        feasible_mask = (G <= 0).all(axis=1) if G is not None else None

        if feasible_mask is not None and feasible_mask.any():
            F_feas = F[feasible_mask]
            best_z1 = float(-F_feas[:, 0].min())  # -F[0] est negatif → min
            best_z2 = float(F_feas[:, 1].min())
            n_feas = int(feasible_mask.sum())
        else:
            # Aucune solution faisable a cette generation
            best_z1 = 0.0
            best_z2 = 0.0
            n_feas = 0

        # Moyennes sur toute la pop (feasible ou non)
        mean_z1 = float(-F[:, 0].mean())
        mean_z2 = float(F[:, 1].mean())

        # Taille du front non-domine
        n_pareto = 0
        if hasattr(algorithm, "opt") and algorithm.opt is not None:
            n_pareto = len(algorithm.opt)

        self.data["generation"].append(gen)
        self.data["best_Z1"].append(best_z1)
        self.data["best_Z2"].append(best_z2)
        self.data["mean_Z1"].append(mean_z1)
        self.data["mean_Z2"].append(mean_z2)
        self.data["n_feasible"].append(n_feas)
        self.data["n_pareto"].append(n_pareto)


class ProblemeTrefilage(ElementwiseProblem):
    """
    Définition du problème d'optimisation pour pymoo.

    pymoo a besoin d'une classe qui hérite de ElementwiseProblem
    et qui implémente la méthode `_evaluate(x, out)`.

    x : tableau des 11 variables de décision
    out : dictionnaire à remplir avec :
        out['F'] : valeurs des fonctions objectifs
        out['G'] : valeurs des contraintes (négatif = OK)
    """

    def __init__(self, parametres_fixes):
        """
        Initialise le problème d'optimisation.

        Parameters
        ----------
        parametres_fixes : dict
            Paramètres qui ne sont PAS optimisés
            (matériau, géométrie de base, conditions ambiantes, etc.)
        """
        # ─── Définition des bornes des variables de décision ───
        # x[0]  : v_f      ∈ [10, 30] m/s
        # x[1]  : mu_0     ∈ [0.02, 0.10]
        # x[2..10] : alpha_1..alpha_9 ∈ [4, 12] degrés
        xl = np.array([10.0, 0.02] + [4.0] * 9)   # bornes inférieures
        xu = np.array([30.0, 0.10] + [12.0] * 9)  # bornes supérieures

        super().__init__(
            n_var=11,        # 11 variables de décision
            n_obj=2,         # 2 fonctions objectifs (Z1, Z2)
            n_constr=4,      # 4 contraintes (C1, C2, C3, C4)
            xl=xl,
            xu=xu,
        )

        self.parametres_fixes = parametres_fixes

    def _evaluate(self, x, out, *args, **kwargs):
        """
        Évalue les fonctions objectifs et les contraintes pour un individu x.

        Conventions pymoo :
        - F : MINIMISE par défaut → on met -Z1 pour maximiser Z1
        - G : violation des contraintes
              G[i] <= 0 → contrainte respectée
              G[i] >  0 → contrainte violée

        Les seuils des contraintes peuvent etre surcharges via parametres_fixes :
            - sigma_safety_factor (defaut 0.6)
            - T_max_C             (defaut 140)
            - mu_critique_factor  (defaut 1.5)
            - P_moteur_nominal    (defaut MACHINE_DEFAULTS)
        """
        # ─── Extraction des variables de décision ───
        v_f = x[0]
        mu_0 = x[1]
        alphas = list(x[2:11])  # 9 angles

        # ─── Construction du dictionnaire de paramètres complet ───
        parametres = self.parametres_fixes.copy()
        parametres.update({
            'v_f': v_f,
            'mu_0': mu_0,
            'alphas': alphas,
        })

        # ─── Lecture des seuils (surcharges utilisateur ou defauts) ───
        sigma_factor = parametres.get('sigma_safety_factor',
                                       SAFETY_CONSTRAINTS['sigma_safety_factor'])
        T_max_seuil = parametres.get('T_max_C', SAFETY_CONSTRAINTS['T_max_C'])
        mu_factor = parametres.get('mu_critique_factor',
                                    SAFETY_CONSTRAINTS['mu_critique_factor'])
        P_nom = parametres.get('P_moteur_nominal',
                                MACHINE_DEFAULTS['P_moteur_nominal'])

        # ─── Simulation du scénario ───
        try:
            resultat = simuler_scenario(parametres)
        except Exception:
            # En cas d'erreur, on pénalise l'individu
            out['F'] = np.array([0.0, 1e6])  # Z1 nul, Z2 énorme
            out['G'] = np.array([1.0, 1.0, 1.0, 1.0])  # toutes violées
            return

        kpis = resultat['KPIs']
        securite = resultat['securite']

        # ─── Calcul des fonctions objectifs ───
        Z1_neg = -kpis['Z1_production_t_jour']
        Z2 = kpis['Z2_SEC_kWh_tonne']
        out['F'] = np.array([Z1_neg, Z2])

        # ─── Calcul des contraintes (G <= 0 = OK) ───
        # C1 : Mécanique
        ratio_meca_max = max(s['ratio'] for s in securite['C1_mecanique']['detail'])
        G1 = ratio_meca_max - sigma_factor

        # C2 : Thermique
        T_max = kpis['T_max_C']
        G2 = (T_max - T_max_seuil) / 100.0

        # C3 : Moteur
        P_total = kpis['P_totale_kW']
        G3 = (P_total - P_nom) / max(P_nom, 1e-3)

        # C4 : Tribologique
        mu_max = kpis['mu_max']
        G4 = (mu_max - mu_factor * mu_0) / max(mu_0, 1e-3)

        out['G'] = np.array([G1, G2, G3, G4])


def lancer_optimisation(parametres_fixes,
                          taille_population=None,
                          n_generations=None,
                          afficher_progression=True):
    """
    ⭐ FONCTION PRINCIPALE : lance l'optimisation NSGA-II.

    Parameters
    ----------
    parametres_fixes : dict
        Paramètres NON optimisés (matériau, géométrie, etc.)
    taille_population : int
        Nombre d'individus par génération (par défaut 100)
    n_generations : int
        Nombre de générations (par défaut 200)
    afficher_progression : bool
        Si True, affiche la progression dans la console

    Returns
    -------
    dict avec :
        - 'pareto_X'        : array des solutions Pareto-optimales
                              (chaque ligne = un individu, 11 colonnes)
        - 'pareto_F'        : array des objectifs (n_solutions, 2)
                              Colonne 0 : -Z1 (production)
                              Colonne 1 : +Z2 (SEC)
        - 'pareto_solutions': list of dict avec valeurs lisibles
        - 'n_evaluations'   : nombre total d'évaluations effectuées
        - 'temps_calcul_s'  : temps d'exécution [s]
    """
    import time

    if not PYMOO_AVAILABLE:
        raise RuntimeError(
            "Le module pymoo n'est pas installé. "
            "Installez-le avec : pip install pymoo  "
            f"(détail: {PYMOO_ERROR})"
        )

    # Paramètres par défaut
    if taille_population is None:
        taille_population = NSGA2_PARAMS['pop_size']
    if n_generations is None:
        n_generations = NSGA2_PARAMS['n_generations']

    # ─── Création du problème ───
    probleme = ProblemeTrefilage(parametres_fixes)

    # ─── Configuration de NSGA-II ───
    algorithme = NSGA2(
        pop_size=taille_population,
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(eta=20),
        eliminate_duplicates=True,
    )

    # ─── Critère d'arrêt : nombre de générations ───
    arret = get_termination("n_gen", n_generations)

    # ─── Callback de capture d'historique pour graphique de convergence ───
    history = HistoryCallback()

    # ─── Lancement de l'optimisation ───
    t_debut = time.time()
    resultat = minimize(
        probleme,
        algorithme,
        arret,
        seed=42,           # graine pour reproductibilité
        verbose=afficher_progression,
        callback=history,
    )
    t_fin = time.time()

    # ─── Extraction des résultats ───
    pareto_X = resultat.X  # solutions
    pareto_F = resultat.F  # objectifs

    # Conversion en format lisible
    pareto_solutions = []
    if pareto_X is not None and len(pareto_X) > 0:
        for i in range(len(pareto_X)):
            x = pareto_X[i]
            f = pareto_F[i]
            pareto_solutions.append({
                'index': i,
                'v_f': float(x[0]),
                'mu_0': float(x[1]),
                'alphas': [float(a) for a in x[2:11]],
                'Z1_production_t_jour': float(-f[0]),  # remettre en positif
                'Z2_SEC_kWh_tonne': float(f[1]),
            })

    return {
        'pareto_X': pareto_X,
        'pareto_F': pareto_F,
        'pareto_solutions': pareto_solutions,
        'n_evaluations': resultat.algorithm.evaluator.n_eval,
        'temps_calcul_s': t_fin - t_debut,
        'n_solutions_pareto': len(pareto_X) if pareto_X is not None else 0,
        'history': dict(history.data),  # courbes d'evolution par generation
    }


def identifier_points_caracteristiques(pareto_solutions):
    """
    Identifie les 3 points caractéristiques du front de Pareto :
        - BOOST     : production maximale
        - ECO       : SEC minimale
        - COMPROMIS : équilibre (point du genou)

    Parameters
    ----------
    pareto_solutions : list of dict
        Solutions Pareto issues de lancer_optimisation()

    Returns
    -------
    dict avec :
        - 'boost'     : la solution avec Z1 maximum
        - 'eco'       : la solution avec Z2 minimum
        - 'compromis' : la solution la plus équilibrée
    """
    if not pareto_solutions:
        return {'boost': None, 'eco': None, 'compromis': None}

    # BOOST : production maximale
    boost = max(pareto_solutions, key=lambda s: s['Z1_production_t_jour'])

    # ECO : SEC minimale
    eco = min(pareto_solutions, key=lambda s: s['Z2_SEC_kWh_tonne'])

    # COMPROMIS : point le plus proche de la diagonale (méthode du genou)
    # On normalise puis on cherche la distance min à l'utopie (0, 0)
    Z1_max = max(s['Z1_production_t_jour'] for s in pareto_solutions)
    Z2_min = min(s['Z2_SEC_kWh_tonne'] for s in pareto_solutions)
    Z1_min = min(s['Z1_production_t_jour'] for s in pareto_solutions)
    Z2_max = max(s['Z2_SEC_kWh_tonne'] for s in pareto_solutions)

    def distance_compromis(s):
        # Normalisation [0, 1]
        z1_norm = (s['Z1_production_t_jour'] - Z1_min) / max(Z1_max - Z1_min, 1e-9)
        z2_norm = (s['Z2_SEC_kWh_tonne'] - Z2_min) / max(Z2_max - Z2_min, 1e-9)
        # Distance euclidienne au point idéal (1, 0)
        return np.sqrt((1 - z1_norm) ** 2 + z2_norm ** 2)

    compromis = min(pareto_solutions, key=distance_compromis)

    return {
        'boost': boost,
        'eco': eco,
        'compromis': compromis,
    }


# ═══════════════════════════════════════════════════════════════════
# TEST RAPIDE (NE PAS LANCER SAUF SI VOUS ATTENDEZ ~3 MINUTES)
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("TEST DU MODULE OPTIMIZER (NSGA-II)")
    print("ATTENTION : ce test peut prendre 1-3 minutes")
    print("=" * 60)

    parametres_fixes = {
        'K': 335.0, 'n': 0.50,
        'd_0': 8.0, 'd_f': 2.0, 'n_passes': 9,
        'beta': 0.25, 'gamma': 1e-6, 'Q_lub': 70000.0,
        'T_ambient_C': 25.0,
        'age_lubrifiant_jours': 30,
    }

    print("\nLancement de NSGA-II avec petite population (50 ind., 30 gén.)...")
    resultat = lancer_optimisation(
        parametres_fixes,
        taille_population=50,
        n_generations=30,
        afficher_progression=True,
    )

    print(f"\n--- RÉSULTATS ---")
    print(f"Nombre de solutions Pareto : {resultat['n_solutions_pareto']}")
    print(f"Nombre total d'évaluations : {resultat['n_evaluations']}")
    print(f"Temps de calcul            : {resultat['temps_calcul_s']:.1f} s")

    if resultat['pareto_solutions']:
        points = identifier_points_caracteristiques(resultat['pareto_solutions'])
        print(f"\n--- POINTS CARACTÉRISTIQUES ---")
        print(f"\n🚀 BOOST :")
        print(f"   Z1 = {points['boost']['Z1_production_t_jour']:.2f} t/jour")
        print(f"   Z2 = {points['boost']['Z2_SEC_kWh_tonne']:.2f} kWh/t")
        print(f"\n🌿 ECO :")
        print(f"   Z1 = {points['eco']['Z1_production_t_jour']:.2f} t/jour")
        print(f"   Z2 = {points['eco']['Z2_SEC_kWh_tonne']:.2f} kWh/t")
        print(f"\n⚖️ COMPROMIS :")
        print(f"   Z1 = {points['compromis']['Z1_production_t_jour']:.2f} t/jour")
        print(f"   Z2 = {points['compromis']['Z2_SEC_kWh_tonne']:.2f} kWh/t")

    print("\n✅ Optimisation terminée !")
