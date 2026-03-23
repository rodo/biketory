"""Catalogue of all 43 Biketory badges, grouped by category."""

BADGE_CATALOGUE = [
    {
        "category": "Territoire",
        "badges": [
            {"id": "territoire_premier", "name": "Premier pas", "desc": "Conquérir son 1er hexagone"},
            {"id": "territoire_explorateur", "name": "Explorateur", "desc": "100 hexagones conquis"},
            {"id": "territoire_conquerant", "name": "Conquérant", "desc": "500 hexagones conquis"},
            {"id": "territoire_seigneur", "name": "Seigneur", "desc": "2 000 hexagones conquis"},
            {"id": "territoire_legende", "name": "Légende", "desc": "10 000 hexagones conquis"},
        ],
    },
    {
        "category": "Activité",
        "badges": [
            {"id": "activite_premier_trace", "name": "Premier tracé", "desc": "Uploader sa 1ère trace GPX"},
            {"id": "activite_regulier", "name": "Régulier", "desc": "7 jours consécutifs avec une trace"},
            {"id": "activite_centurion", "name": "Centurion", "desc": "100 traces uploadées"},
            {"id": "activite_randonneur", "name": "Randonneur", "desc": "Trace > 100 km"},
        ],
    },
    {
        "category": "Social",
        "badges": [
            {"id": "social_premier_ami", "name": "Premier ami", "desc": "Ajouter son 1er ami"},
            {"id": "social_communaute", "name": "Communauté", "desc": "10 amis ajoutés"},
        ],
    },
    {
        "category": "Surfaces",
        "badges": [
            {"id": "surfaces_geometre", "name": "Géomètre", "desc": "1ère surface fermée détectée"},
            {"id": "surfaces_architecte", "name": "Architecte", "desc": "50 surfaces fermées détectées"},
        ],
    },
    {
        "category": "Spécial",
        "badges": [
            {"id": "special_nuit_noire", "name": "Nuit noire", "desc": "Trace uploadée entre 0h et 5h"},
            {"id": "special_indestructible", "name": "Indestructible", "desc": "Conserver un hexagone 30 jours"},
            {"id": "special_sprint", "name": "Sprint", "desc": "Vitesse moyenne > 35 km/h"},
        ],
    },
    {
        "category": "Séries quotidiennes",
        "badges": [
            {"id": "quotidien_3j", "name": "Flamme", "desc": "3 jours consécutifs"},
            {"id": "quotidien_7j", "name": "Série 7j", "desc": "7 jours consécutifs"},
            {"id": "quotidien_14j", "name": "Série 14j", "desc": "14 jours consécutifs"},
            {"id": "quotidien_30j", "name": "Mois de feu", "desc": "30 jours consécutifs"},
            {"id": "quotidien_100j", "name": "Centenaire", "desc": "100 jours consécutifs"},
        ],
    },
    {
        "category": "Séries hebdomadaires",
        "badges": [
            {"id": "hebdo_2sem", "name": "Régulier", "desc": "1 trace/semaine, 2 semaines de suite"},
            {"id": "hebdo_4sem", "name": "Rythme", "desc": "1 trace/semaine, 4 semaines de suite"},
            {"id": "hebdo_8sem", "name": "Cadencé", "desc": "1 trace/semaine, 8 semaines de suite"},
            {"id": "hebdo_26sem", "name": "Semestriel", "desc": "1 trace/semaine, 26 semaines de suite"},
            {"id": "hebdo_52sem", "name": "Toutes saisons", "desc": "1 trace/semaine, 52 semaines de suite"},
        ],
    },
    {
        "category": "Séries mensuelles",
        "badges": [
            {"id": "mensuel_2m", "name": "Assidu", "desc": "1 trace/mois pendant 2 mois"},
            {"id": "mensuel_3m", "name": "Saison", "desc": "1 trace/mois pendant 3 mois"},
            {"id": "mensuel_6m", "name": "Mi-année", "desc": "1 trace/mois pendant 6 mois"},
            {"id": "mensuel_12m", "name": "Une année", "desc": "1 trace/mois pendant 12 mois"},
        ],
    },
    {
        "category": "Volume hebdomadaire",
        "badges": [
            {"id": "volume_2x", "name": "Duo", "desc": "2 traces/sem pendant 4 semaines"},
            {"id": "volume_3x", "name": "Trio", "desc": "3 traces/sem pendant 4 semaines"},
            {"id": "volume_5x", "name": "Machine", "desc": "5 traces/sem pendant 4 semaines"},
            {"id": "volume_7x", "name": "Quotidien", "desc": "7 traces/sem pendant 4 semaines"},
        ],
    },
    {
        "category": "Saisonnier",
        "badges": [
            {"id": "saison_printemps", "name": "Printemps", "desc": "1 trace/sem de mars à mai"},
            {"id": "saison_ete", "name": "Été", "desc": "1 trace/sem de juin à août"},
            {"id": "saison_automne", "name": "Automne", "desc": "1 trace/sem de septembre à novembre"},
            {"id": "saison_hiver", "name": "Hiver", "desc": "1 trace/sem de décembre à février"},
            {"id": "saison_4saisons", "name": "4 saisons", "desc": "Obtenir les 4 badges saisonniers"},
        ],
    },
    {
        "category": "Distance",
        "badges": [
            {"id": "dist_100", "name": "Centurion km", "desc": "100 km parcourus en 1 mois"},
            {"id": "dist_500", "name": "Rouleur", "desc": "500 km parcourus en 1 mois"},
            {"id": "dist_1000", "name": "Forçat", "desc": "1000 km parcourus en 1 mois"},
            {"id": "dist_10000", "name": "Odyssée", "desc": "10 000 km au compteur total"},
        ],
    },
]
