"""Catalogue of all 43 Biketory badges, grouped by category."""

from django.utils.translation import gettext_lazy as _

BADGE_CATALOGUE = [
    {
        "category": _("Territory"),
        "badges": [
            {"id": "territoire_premier", "name": _("First step"), "desc": _("Conquer your 1st hexagon")},
            {"id": "territoire_explorateur", "name": _("Explorer"), "desc": _("100 hexagons conquered")},
            {"id": "territoire_conquerant", "name": _("Conqueror"), "desc": _("500 hexagons conquered")},
            {"id": "territoire_seigneur", "name": _("Lord"), "desc": _("2,000 hexagons conquered")},
            {"id": "territoire_legende", "name": _("Legend"), "desc": _("10,000 hexagons conquered")},
        ],
    },
    {
        "category": _("Activity"),
        "badges": [
            {"id": "activite_premier_trace", "name": _("First trace"), "desc": _("Upload your 1st GPX trace")},
            {"id": "activite_regulier", "name": _("Regular"), "desc": _("7 consecutive days with a trace")},
            {"id": "activite_centurion", "name": _("Centurion"), "desc": _("100 traces uploaded")},
            {"id": "activite_randonneur", "name": _("Hiker"), "desc": _("Trace > 100 km")},
        ],
    },
    {
        "category": _("Social"),
        "badges": [
            {"id": "social_premier_ami", "name": _("First friend"), "desc": _("Add your 1st friend")},
            {"id": "social_communaute", "name": _("Community"), "desc": _("10 friends added")},
        ],
    },
    {
        "category": _("Surfaces"),
        "badges": [
            {"id": "surfaces_geometre", "name": _("Surveyor"), "desc": _("1st closed surface detected")},
            {"id": "surfaces_architecte", "name": _("Architect"), "desc": _("50 closed surfaces detected")},
        ],
    },
    {
        "category": _("Special"),
        "badges": [
            {"id": "special_nuit_noire", "name": _("Dark night"), "desc": _("Trace uploaded between 0am and 5am")},
            {"id": "special_indestructible", "name": _("Indestructible"), "desc": _("Keep a hexagon for 30 days")},
            {"id": "special_sprint", "name": _("Sprint"), "desc": _("Average speed > 35 km/h")},
        ],
    },
    {
        "category": _("Daily streaks"),
        "badges": [
            {"id": "quotidien_3j", "name": _("Flame"), "desc": _("3 consecutive days")},
            {"id": "quotidien_7j", "name": _("7-day streak"), "desc": _("7 consecutive days")},
            {"id": "quotidien_14j", "name": _("14-day streak"), "desc": _("14 consecutive days")},
            {"id": "quotidien_30j", "name": _("Month of fire"), "desc": _("30 consecutive days")},
            {"id": "quotidien_100j", "name": _("Centenarian"), "desc": _("100 consecutive days")},
        ],
    },
    {
        "category": _("Weekly streaks"),
        "badges": [
            {"id": "hebdo_2sem", "name": _("Regular"), "desc": _("1 trace/week for 2 weeks in a row")},
            {"id": "hebdo_4sem", "name": _("Rhythm"), "desc": _("1 trace/week for 4 weeks in a row")},
            {"id": "hebdo_8sem", "name": _("Cadenced"), "desc": _("1 trace/week for 8 weeks in a row")},
            {"id": "hebdo_26sem", "name": _("Half-year"), "desc": _("1 trace/week for 26 weeks in a row")},
            {"id": "hebdo_52sem", "name": _("All seasons"), "desc": _("1 trace/week for 52 weeks in a row")},
        ],
    },
    {
        "category": _("Monthly streaks"),
        "badges": [
            {"id": "mensuel_2m", "name": _("Dedicated"), "desc": _("1 trace/month for 2 months")},
            {"id": "mensuel_3m", "name": _("Season"), "desc": _("1 trace/month for 3 months")},
            {"id": "mensuel_6m", "name": _("Half-year"), "desc": _("1 trace/month for 6 months")},
            {"id": "mensuel_12m", "name": _("One year"), "desc": _("1 trace/month for 12 months")},
        ],
    },
    {
        "category": _("Weekly volume"),
        "badges": [
            {"id": "volume_2x", "name": _("Duo"), "desc": _("2 traces/week for 4 weeks")},
            {"id": "volume_3x", "name": _("Trio"), "desc": _("3 traces/week for 4 weeks")},
            {"id": "volume_5x", "name": _("Machine"), "desc": _("5 traces/week for 4 weeks")},
            {"id": "volume_7x", "name": _("Daily"), "desc": _("7 traces/week for 4 weeks")},
        ],
    },
    {
        "category": _("Seasonal"),
        "badges": [
            {"id": "saison_printemps", "name": _("Spring"), "desc": _("1 trace from March to May")},
            {"id": "saison_ete", "name": _("Summer"), "desc": _("1 trace from June to August")},
            {"id": "saison_automne", "name": _("Autumn"), "desc": _("1 trace from September to November")},
            {"id": "saison_hiver", "name": _("Winter"), "desc": _("1 trace from December to February")},
            {"id": "saison_4saisons", "name": _("4 seasons"), "desc": _("Earn all 4 seasonal badges")},
        ],
    },
    {
        "category": _("Distance"),
        "badges": [
            {"id": "dist_100", "name": _("Centurion km"), "desc": _("100 km covered in 1 month")},
            {"id": "dist_500", "name": _("Roller"), "desc": _("500 km covered in 1 month")},
            {"id": "dist_1000", "name": _("Ironman"), "desc": _("1,000 km covered in 1 month")},
            {"id": "dist_10000", "name": _("Odyssey"), "desc": _("10,000 km total on the odometer")},
        ],
    },
]
