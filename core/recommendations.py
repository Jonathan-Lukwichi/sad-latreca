"""
═══════════════════════════════════════════════════════════════════════
MOTEUR DE RECOMMANDATIONS INTELLIGENT
═══════════════════════════════════════════════════════════════════════

Genere des actions concretes, quantifiees et ordonnees par impact a
partir de l'etat reel de la ligne (resultat de simuler_scenario) et,
optionnellement, du front de Pareto NSGA-II.

Trois modes :
    1. analyser_etat(resultat)         -> actions par module (sans Pareto)
    2. comparer_pareto(actuel, pareto) -> ecarts vs meilleure solution
    3. diagnostic_global(...)          -> synthese 3 voies pour Analyse globale
═══════════════════════════════════════════════════════════════════════
"""

from typing import Optional


# Seuils utilises pour classifier les ecarts (en pourcentage de marge)
SEUIL_CRITIQUE = 0.0     # marge negative -> critique
SEUIL_VIGILANCE = 0.10   # < 10% de marge -> vigilance


def _severite(marge_relative: float) -> str:
    """Classe une marge relative (0.0 = limite, 1.0 = sain) en niveau."""
    if marge_relative < SEUIL_CRITIQUE:
        return "critique"
    if marge_relative < SEUIL_VIGILANCE:
        return "vigilance"
    return "ok"


def analyser_thermique(resultat: dict, T_seuil: float = 140.0) -> list:
    """Genere des actions thermiques a partir du resultat couple."""
    actions = []
    kpis = resultat.get('KPIs', {})
    T_max = float(kpis.get('T_max_C', 0.0))
    delta_T_list = resultat.get('delta_T', []) or []

    marge = (T_seuil - T_max) / T_seuil if T_seuil else 0.0
    sev = _severite(marge)

    if sev == "critique":
        # Identifier la passe la plus chaude
        idx_max = (max(range(len(delta_T_list)),
                       key=lambda i: float(delta_T_list[i]))
                   if delta_T_list else -1)
        depasse = T_max - T_seuil
        actions.append({
            "module": "Thermique",
            "severite": "critique",
            "titre": f"Depassement thermique de {depasse:+.0f} °C",
            "constat": (f"T_max = {T_max:.0f} °C (seuil {T_seuil:.0f} °C). "
                        f"Pic d'echauffement passe {idx_max + 1} : "
                        f"ΔT = {float(delta_T_list[idx_max]):.0f} °C."
                        if idx_max >= 0
                        else f"T_max = {T_max:.0f} °C > seuil {T_seuil:.0f} °C."),
            "actions": [
                "Augmenter le refroidissement inter-passes η a 0.75-0.80 "
                "(page Configuration).",
                "Reduire la vitesse de sortie v_f de 2-3 m/s pour baisser "
                "directement la dissipation par friction.",
                f"Repenser l'angle 2α de la passe {idx_max + 1} "
                "(verifier qu'il reste dans 6-9°)."
                if idx_max >= 0 else
                "Repartir les reductions plus uniformement entre passes.",
            ],
            "gain_estime": f"-{int(depasse + 10)} °C avec η=0.80",
        })
    elif sev == "vigilance":
        actions.append({
            "module": "Thermique",
            "severite": "vigilance",
            "titre": f"Marge thermique faible : {T_seuil - T_max:+.0f} °C",
            "constat": (f"T_max = {T_max:.0f} °C, soit {marge * 100:.0f}% "
                        f"de marge avant le seuil critique."),
            "actions": [
                "Surveiller l'evolution sur 24h.",
                "Monter η a 0.75 si la production doit augmenter.",
            ],
            "gain_estime": "marge x2",
        })
    else:
        actions.append({
            "module": "Thermique",
            "severite": "ok",
            "titre": f"Fonctionnement nominal ({T_max:.0f} °C)",
            "constat": (f"Marge confortable : {T_seuil - T_max:+.0f} °C "
                        f"avant seuil. Possible d'augmenter la cadence."),
            "actions": [
                "Tester +5 % de vitesse pour exploiter la marge.",
            ],
            "gain_estime": f"+{int(0.05 * float(kpis.get('Z1_production_t_jour', 0))) :.1f} t/jour potentiels",
        })
    return actions


def analyser_mecanique(resultat: dict, sigma_factor: float = 0.6) -> list:
    """Genere des actions mecaniques (forces et contraintes)."""
    actions = []
    securite_C1 = resultat.get('securite', {}).get('C1_mecanique', {})
    detail = securite_C1.get('detail', []) or []
    if not detail:
        return actions

    ratios = [float(s['ratio']) for s in detail]
    ratio_max = max(ratios)
    idx_max = ratios.index(ratio_max)
    marge = (sigma_factor - ratio_max) / sigma_factor

    sev = _severite(marge)

    if sev == "critique":
        actions.append({
            "module": "Forces",
            "severite": "critique",
            "titre": f"Risque rupture passe {idx_max + 1}",
            "constat": (f"Ratio σ_d/σ_y = {ratio_max:.2f} > seuil "
                        f"{sigma_factor:.2f} (passe {idx_max + 1})."),
            "actions": [
                f"Augmenter l'angle 2α de la passe {idx_max + 1} "
                "(de 1-2° pour reduire la force).",
                "Reduire la reduction de section sur cette passe.",
                "Verifier l'usure de la filiere (carbure WC).",
            ],
            "gain_estime": "-15-20% de force d'etirage",
        })
    elif sev == "vigilance":
        actions.append({
            "module": "Forces",
            "severite": "vigilance",
            "titre": f"Marge mecanique faible passe {idx_max + 1}",
            "constat": (f"Ratio σ_d/σ_y = {ratio_max:.2f} "
                        f"(seuil {sigma_factor:.2f})."),
            "actions": [
                "Surveiller l'usure des filieres en sortie de passe "
                f"{idx_max + 1}.",
                "Eviter d'augmenter la vitesse au-dela de la valeur "
                "courante.",
            ],
            "gain_estime": "fiabilite +20%",
        })
    return actions


def analyser_lubrification(resultat: dict) -> list:
    """Genere des actions sur le lubrifiant a partir de μ."""
    actions = []
    kpis = resultat.get('KPIs', {})
    mu_max = float(kpis.get('mu_max', 0.0))
    mu_par_passe = resultat.get('mu_par_passe', []) or []
    if not mu_par_passe:
        return actions
    mu_initial = float(mu_par_passe[0])
    if mu_initial <= 0:
        return actions

    ratio = mu_max / mu_initial

    if ratio > 1.5:
        actions.append({
            "module": "Lubrification",
            "severite": "critique",
            "titre": "Lubrifiant degrade",
            "constat": (f"μ a augmente de {(ratio - 1) * 100:.0f}% "
                        f"(initial {mu_initial:.3f} -> max {mu_max:.3f})."),
            "actions": [
                "Remplacer le lubrifiant immediatement.",
                "Verifier la temperature du bain (cible < 40°C).",
            ],
            "gain_estime": "-30% de force d'etirage apres remplacement",
        })
    elif ratio > 1.2:
        actions.append({
            "module": "Lubrification",
            "severite": "vigilance",
            "titre": "Lubrifiant en fin de vie",
            "constat": (f"μ a augmente de {(ratio - 1) * 100:.0f}%. "
                        "Remplacement recommande sous 15 jours."),
            "actions": [
                "Planifier le remplacement.",
                "Reduire l'age max de service de 10%.",
            ],
            "gain_estime": "stabilite procedee +1 mois",
        })
    return actions


def comparer_pareto(resultat_actuel: dict,
                     point_pareto: dict) -> Optional[dict]:
    """
    Compare la config actuelle a UNE solution Pareto (typiquement compromis).
    Retourne un diagnostic chiffre pret a afficher.
    """
    if not point_pareto:
        return None

    kpis = resultat_actuel.get('KPIs', {})
    z1_act = float(kpis.get('Z1_production_t_jour', 0.0))
    z2_act = float(kpis.get('Z2_SEC_kWh_tonne', 0.0))
    z1_opt = float(point_pareto.get('Z1_production_t_jour', 0.0))
    z2_opt = float(point_pareto.get('Z2_SEC_kWh_tonne', 0.0))

    delta_z1 = z1_opt - z1_act
    delta_z2 = z2_opt - z2_act
    pct_z1 = (delta_z1 / z1_act * 100) if z1_act > 0 else 0.0
    pct_z2 = (delta_z2 / z2_act * 100) if z2_act > 0 else 0.0

    v_f_opt = float(point_pareto.get('v_f', 0.0))
    mu_0_opt = float(point_pareto.get('mu_0', 0.0))
    alphas_opt = point_pareto.get('alphas') or []
    alpha_moy = (sum(float(a) for a in alphas_opt) / len(alphas_opt)
                 if alphas_opt else 0.0)

    # Ordonner les leviers du plus impactant au moins impactant
    leviers = []
    if abs(pct_z1) > 5 or abs(pct_z2) > 5:
        leviers.append(f"vitesse v_f → {v_f_opt:.1f} m/s")
        leviers.append(f"frottement μ₀ → {mu_0_opt:.3f}")
        leviers.append(f"angle moyen 2α → {alpha_moy:.1f}°")

    return {
        "delta_production_t_jour": delta_z1,
        "delta_production_pct": pct_z1,
        "delta_sec_kWh_t": delta_z2,
        "delta_sec_pct": pct_z2,
        "v_f_optimal": v_f_opt,
        "mu_0_optimal": mu_0_opt,
        "alpha_moyen_optimal": alpha_moy,
        "leviers_ordonnes": leviers,
    }


def diagnostic_global(resultat_actuel: dict,
                       reference: Optional[dict] = None,
                       optimisation: Optional[dict] = None,
                       T_seuil: float = 140.0) -> dict:
    """
    Synthese complete pour l'Analyse Globale : 3 voies + actions.

    Returns
    -------
    dict avec :
        - 'actions' : liste d'actions tous modules (triee par severite)
        - 'comparaison_pareto' : ecarts vs solution NSGA-II compromis
        - 'severite_globale' : 'critique' / 'vigilance' / 'ok'
        - 'verdict' : phrase de synthese
    """
    actions = []
    actions.extend(analyser_thermique(resultat_actuel, T_seuil))
    actions.extend(analyser_mecanique(resultat_actuel))
    actions.extend(analyser_lubrification(resultat_actuel))

    # Tri par severite (critique d'abord)
    ordre = {"critique": 0, "vigilance": 1, "ok": 2}
    actions.sort(key=lambda a: ordre.get(a.get('severite', 'ok'), 3))

    severites = [a['severite'] for a in actions]
    if 'critique' in severites:
        sev_globale = 'critique'
    elif 'vigilance' in severites:
        sev_globale = 'vigilance'
    else:
        sev_globale = 'ok'

    comparaison = None
    if optimisation and isinstance(optimisation, dict):
        compromis = optimisation.get('compromis')
        if compromis:
            comparaison = comparer_pareto(resultat_actuel, compromis)

    # Verdict synthetique
    if sev_globale == 'critique':
        verdict = ("La ligne fonctionne hors zone de securite. "
                   "Appliquer les actions critiques immediatement.")
    elif sev_globale == 'vigilance':
        verdict = ("La ligne reste fonctionnelle mais une derive est "
                   "detectee. Planifier les actions sous 7 jours.")
    else:
        verdict = ("La ligne fonctionne dans la zone optimale. "
                   "Marges suffisantes pour augmenter la cadence.")

    if comparaison and comparaison['delta_production_pct'] > 5:
        verdict += (f" Le NSGA-II identifie un gain de "
                    f"{comparaison['delta_production_pct']:+.0f}% de production "
                    f"realisable.")

    return {
        "actions": actions,
        "comparaison_pareto": comparaison,
        "severite_globale": sev_globale,
        "verdict": verdict,
    }
