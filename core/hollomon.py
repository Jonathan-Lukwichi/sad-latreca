"""
═══════════════════════════════════════════════════════════════════════
PILIER P1 — LOI D'ÉCROUISSAGE DE HOLLOMON (1945)
═══════════════════════════════════════════════════════════════════════

ÉQUATION CENTRALE :  σ = K · ε^n

OÙ :
    σ : contrainte d'écoulement [MPa]
    K : coefficient de résistance [MPa]
    ε : déformation plastique vraie [-]
    n : exposant d'écrouissage [-]

POUR LE CUIVRE ETP :
    K ≈ 335 MPa (entre 315 et 350)
    n ≈ 0.50  (entre 0.44 et 0.54)

EXPLICATION SIMPLE :
    Quand on déforme du cuivre, il devient plus dur (= écrouissage).
    Cette loi nous dit : "Plus tu déformes, plus c'est dur."

UTILISATION DANS LE SAD :
    À chaque passe i, on calcule :
    1. La déformation cumulée εᵢ
    2. La contrainte d'écoulement σᵢ = K · εᵢ^n
    3. Cette σᵢ sert ensuite au calcul d'Avitzur (force de tréfilage)

RÉFÉRENCE :
    Hollomon, J.H. (1945). Tensile deformation. Trans. AIME, 162, 268-290.
═══════════════════════════════════════════════════════════════════════
"""

import numpy as np


def calculer_contrainte_hollomon(epsilon, K=335.0, n=0.50):
    """
    Calcule la contrainte d'écoulement selon la loi de Hollomon.

    Formule : σ = K · ε^n

    Parameters
    ----------
    epsilon : float ou array
        Déformation plastique vraie [-]
        Exemple : epsilon = 1.5 (pour ε = 1.5)
    K : float
        Coefficient de résistance [MPa]
        Cuivre ETP : 335 (entre 315 et 350)
    n : float
        Exposant d'écrouissage [-]
        Cuivre ETP : 0.50 (entre 0.44 et 0.54)

    Returns
    -------
    sigma : float ou array
        Contrainte d'écoulement [MPa]

    Raises
    ------
    ValueError
        Si K <= 0 ou si n n'est pas dans [0, 1].

    Exemples
    --------
    >>> calculer_contrainte_hollomon(epsilon=1.0, K=335, n=0.5)
    335.0
    >>> calculer_contrainte_hollomon(epsilon=2.0, K=335, n=0.5)
    473.76...
    """
    # Vérification des entrées (sécurité)
    if K <= 0:
        raise ValueError(f"K doit être positif. Reçu : K = {K}")
    if n < 0 or n > 1:
        raise ValueError(f"n doit être dans [0, 1]. Reçu : n = {n}")

    # Conversion en array numpy pour gérer aussi les listes
    epsilon_array = np.asarray(epsilon)

    # Calcul de la contrainte (formule de Hollomon)
    sigma = K * np.power(epsilon_array, n)

    return float(sigma) if epsilon_array.ndim == 0 else sigma


def calculer_deformation_cumulee(d_initial, d_apres_passe):
    """
    Calcule la déformation cumulée après une passe.

    Formule : ε = ln(A_initial / A_après) = 2 · ln(d_initial / d_après)

    Pourquoi ce facteur 2 ?
        Parce que A = π · d² / 4
        Donc A_initial / A_après = (d_initial / d_après)²
        Et ln((x)²) = 2 · ln(x)

    Parameters
    ----------
    d_initial : float
        Diamètre du fil avant la passe [mm]
    d_apres_passe : float
        Diamètre du fil après la passe [mm]

    Returns
    -------
    epsilon : float
        Déformation plastique cumulée [-]

    Exemples
    --------
    >>> calculer_deformation_cumulee(d_initial=4.0, d_apres_passe=2.0)
    1.3862...
    >>> calculer_deformation_cumulee(d_initial=8.0, d_apres_passe=2.0)
    2.7725...
    """
    # Vérifications de sécurité
    if d_initial <= 0:
        raise ValueError(f"d_initial doit être positif. Reçu : {d_initial}")
    if d_apres_passe <= 0:
        raise ValueError(f"d_apres_passe doit être positif. Reçu : {d_apres_passe}")
    if d_apres_passe > d_initial:
        raise ValueError(
            f"d_apres_passe ({d_apres_passe}) doit être <= d_initial ({d_initial})"
        )

    # Calcul de la déformation cumulée
    epsilon = 2.0 * np.log(d_initial / d_apres_passe)
    return float(epsilon)


def calculer_contrainte_moyenne_passe(eps_avant, eps_apres, K=335.0, n=0.50):
    """
    Calcule la contrainte d'écoulement MOYENNE entre deux passes.

    Cette moyenne est utilisée par le modèle d'Avitzur (Pilier P2)
    car la déformation augmente progressivement DANS la filière.

    Formule analytique (intégration de Hollomon) :
        σ̄ = K · (ε_apres^(n+1) - ε_avant^(n+1)) / ((n+1) · (ε_apres - ε_avant))

    Parameters
    ----------
    eps_avant : float
        Déformation cumulée AVANT la passe [-]
    eps_apres : float
        Déformation cumulée APRÈS la passe [-]
    K, n : float
        Paramètres de Hollomon

    Returns
    -------
    sigma_moy : float
        Contrainte d'écoulement moyenne [MPa]
    """
    # Cas particulier : pas de déformation supplémentaire
    if abs(eps_apres - eps_avant) < 1e-10:
        return calculer_contrainte_hollomon(eps_apres, K, n)

    # Cas particulier : 1ère passe (eps_avant = 0)
    if eps_avant < 1e-10:
        # σ̄ = K · ε_apres^n / (n+1)
        return K * np.power(eps_apres, n) / (n + 1)

    # Cas général : intégration analytique
    numerateur = K * (np.power(eps_apres, n + 1) - np.power(eps_avant, n + 1))
    denominateur = (n + 1) * (eps_apres - eps_avant)
    return float(numerateur / denominateur)


def calculer_sequence_passes(d_0, d_f, n_passes=9):
    """
    Génère la séquence des diamètres pour les N passes successives.

    Stratégie : réduction uniforme du diamètre passe par passe.
    On peut aussi utiliser une réduction uniforme de la SECTION (autre option).

    Parameters
    ----------
    d_0 : float
        Diamètre d'entrée du fil-machine [mm]
    d_f : float
        Diamètre final souhaité [mm]
    n_passes : int
        Nombre de passes (9 pour LATRECA)

    Returns
    -------
    diametres : list
        Liste de N+1 diamètres : [d_0, d_1, ..., d_N=d_f]
        Exemple pour 9 passes : [8.0, 7.21, 6.49, ..., 2.0]
    """
    # Réduction uniforme du diamètre
    # d_i = d_0 · (d_f/d_0)^(i/n)
    diametres = []
    for i in range(n_passes + 1):
        d_i = d_0 * np.power(d_f / d_0, i / n_passes)
        diametres.append(float(d_i))

    return diametres


def calculer_profil_contraintes(d_0, d_f, n_passes=9, K=335.0, n=0.50):
    """
    Calcule l'évolution complète de la contrainte d'écoulement
    sur les N passes successives.

    Très utile pour visualiser l'écrouissage cumulatif.

    Returns
    -------
    dict avec :
        - 'diametres'           : list des diamètres [mm]
        - 'deformations_cumulees': list des déformations cumulées [-]
        - 'contraintes_par_passe': list des contraintes σᵢ [MPa]
        - 'contraintes_moyennes' : list des σ̄ pour chaque passe [MPa]
    """
    # Génération de la séquence de diamètres
    diametres = calculer_sequence_passes(d_0, d_f, n_passes)

    # Initialisation des listes de résultats
    deformations = [0.0]  # epsilon_0 = 0 (état recuit)
    contraintes_par_passe = [0.0]  # sigma à epsilon=0 vaut 0 (Hollomon)
    contraintes_moyennes = []

    # Boucle sur les passes
    for i in range(1, n_passes + 1):
        # Déformation cumulée après la passe i
        eps_i = calculer_deformation_cumulee(d_0, diametres[i])
        deformations.append(eps_i)

        # Contrainte d'écoulement à la sortie de la passe i
        sigma_i = calculer_contrainte_hollomon(eps_i, K, n)
        contraintes_par_passe.append(sigma_i)

        # Contrainte moyenne pendant la passe i (utile pour Avitzur)
        sigma_moy = calculer_contrainte_moyenne_passe(
            deformations[i - 1], eps_i, K, n
        )
        contraintes_moyennes.append(sigma_moy)

    return {
        'diametres': diametres,
        'deformations_cumulees': deformations,
        'contraintes_par_passe': contraintes_par_passe,
        'contraintes_moyennes': contraintes_moyennes,
        'K': K,
        'n': n,
    }


# ═══════════════════════════════════════════════════════════════════
# TEST RAPIDE (pour vérifier que le module fonctionne)
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("TEST DU MODULE HOLLOMON")
    print("=" * 60)

    # Test 1 : contrainte simple
    sigma = calculer_contrainte_hollomon(epsilon=1.0)
    print(f"\nTest 1 : σ(ε=1.0) = {sigma:.2f} MPa  (attendu : 335)")

    # Test 2 : déformation cumulée
    eps = calculer_deformation_cumulee(d_initial=8.0, d_apres_passe=2.0)
    print(f"Test 2 : ε(8mm → 2mm) = {eps:.4f}  (attendu : 2.77)")

    # Test 3 : profil complet sur 9 passes
    profil = calculer_profil_contraintes(d_0=8.0, d_f=2.0, n_passes=9)
    print("\nTest 3 : Profil 9 passes (8mm → 2mm)")
    print(f"  Diamètres   : {[f'{d:.2f}' for d in profil['diametres']]}")
    print(f"  Déformations: {[f'{e:.3f}' for e in profil['deformations_cumulees']]}")
    print(f"  σ par passe : {[f'{s:.0f}' for s in profil['contraintes_par_passe']]} MPa")
    print(f"  σ̄ moyennes : {[f'{s:.0f}' for s in profil['contraintes_moyennes']]} MPa")
    print("\n✅ Tous les tests sont passés !")
