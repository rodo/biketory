# Types de challenges

Ce document décrit les 7 types de challenges disponibles dans l'application.
Chaque type définit une mécanique de scoring différente.

## Champs communs à tous les challenges

| Champ | Description |
|---|---|
| `title` | Nom du challenge |
| `description` | Description libre |
| `start_date` / `end_date` | Période d'activité |
| `premium_only` | Réservé aux utilisateurs premium |
| `geozone` | Zone géographique optionnelle (FK `GeoZone`) |
| `goal_threshold` | Seuil de score à atteindre pour valider l'objectif (optionnel) |

## 1. `capture_hexagon` — Capturer des hexagones

**Objectif :** acquérir des hexagones parmi un ensemble cible défini par
l'administrateur.

**Score :** nombre d'hexagones cibles (`ChallengeHexagon`) que le participant a
traversés avec au moins une de ses traces.

**Champs spécifiques :**

| Champ | Rôle |
|---|---|
| `capture_mode` | `any` = au moins un hexagone cible suffit pour valider ; `all` = tous les hexagones cibles doivent être acquis |

**SQL :** `challenges/sql/challenge_score_capture.sql`

**Exemple :** « Capturez les 50 hexagones du parc de la Tête d'Or. »

## 2. `max_points` — Maximum de points

**Objectif :** accumuler le plus de points possible sur les hexagones cibles du
challenge pendant la période.

**Score :** somme des `HexagonScore.points` du participant sur les hexagones
cibles, pour les points gagnés pendant la période du challenge.

**Champs spécifiques :** aucun (utilise `ChallengeHexagon` comme
`capture_hexagon`).

**SQL :** `challenges/sql/challenge_score_points.sql`

**Exemple :** « Parcourez le plus possible les hexagones du centre-ville
pendant le mois de juin. » Plus un participant repasse sur les mêmes hexagones,
plus son score augmente.

## 3. `active_days` — Jours d'activité

**Objectif :** être régulier en uploadant des traces sur un maximum de jours
distincts.

**Score :** nombre de jours distincts où le participant a uploadé au moins une
trace pendant la période du challenge.

**Champs spécifiques :** aucun.

**SQL :** `challenges/sql/challenge_score_active_days.sql`

**Exemple :** « Roulez au moins 1 fois par jour pendant 30 jours. » Encourage
la régularité plutôt que le volume.

## 4. `new_hexagons` — Nouveaux hexagones

**Objectif :** explorer de nouveaux territoires en acquérant des hexagones
jamais traversés auparavant.

**Score :** nombre d'hexagones acquis **pour la première fois** pendant la
période du challenge. Les hexagones déjà visités avant le début du challenge ne
comptent pas.

**Champs spécifiques :**

| Champ | Rôle |
|---|---|
| `geozone` | Si défini, seuls les nouveaux hexagones situés dans cette zone comptent |

**SQL :**
- Sans geozone : `challenges/sql/challenge_score_new_hexagons.sql`
- Avec geozone : `challenges/sql/challenge_score_new_hexagons_geozone.sql`

**Exemple :** « Découvrez 100 nouveaux hexagones dans le Rhône en juillet. »

## 5. `distinct_zones` — Zones distinctes

**Objectif :** diversifier ses sorties en couvrant un maximum de zones
géographiques différentes.

**Score :** nombre de `GeoZone` distinctes (au niveau administratif configuré)
dans lesquelles le participant a acquis au moins `hexagons_per_zone` hexagones
pendant la période.

**Champs spécifiques :**

| Champ | Rôle |
|---|---|
| `zone_admin_level` | Niveau administratif OSM des zones (ex : 6 = département, 8 = commune). **Obligatoire.** |
| `hexagons_per_zone` | Nombre minimum d'hexagones à acquérir dans une zone pour qu'elle compte. **Obligatoire.** |

**SQL :** `challenges/sql/challenge_score_distinct_zones.sql`

**Exemple :** « Roulez dans 10 départements différents (au moins 5 hexagones
par département). »

## 6. `dataset_points` — Points de dataset

**Objectif :** collecter des points d'intérêt géographiques importés depuis un
fichier GeoJSON externe.

**Score :** nombre de `DatasetFeature` du dataset lié que le participant a
collectées en passant à proximité avec une trace. Une feature est collectée si
elle se trouve dans un hexagone traversé par la trace.

**Champs spécifiques :**

| Champ | Rôle |
|---|---|
| `dataset` | FK vers le `Dataset` contenant les points d'intérêt. **Obligatoire.** |

**Scoring en temps réel :** contrairement aux autres types, le scoring
`dataset_points` est calculé à l'upload de la trace via `challenges/scoring.py`
(jointure spatiale entre les hexagones de la trace et les features du dataset).
Un trigger SQL auto-incrémente `ChallengeParticipant.score` à chaque insertion
dans `ChallengeDatasetScore`.

**SQL :** `challenges/sql/challenge_score_dataset_points.sql` (leaderboard) et
`challenges/sql/score_dataset_on_upload.sql` (scoring à l'upload).

**Exemple :** « Collectez les 200 fontaines à eau de Lyon en passant devant
chacune d'entre elles. »

## 7. `visit_hexagons` — Hexagones traversés

**Objectif :** accumuler le plus grand nombre de passages sur des hexagones,
quel que soit le territoire.

**Score :** nombre total d'hexagones traversés par toutes les traces uploadées
pendant la période du challenge. Un même hexagone traversé par 2 traces compte
2 fois (pas de dédoublonnage).

**Champs spécifiques :** aucun.

**SQL :** `challenges/sql/challenge_score_visit_hexagons.sql`

**Exemple :** « Traversez 500 hexagones en une semaine, peu importe lesquels. »
Encourage le volume de sorties plutôt que l'exploration.

## Récapitulatif

| Type | Score | Champs requis | Encourage |
|---|---|---|---|
| `capture_hexagon` | Hexagones cibles acquis | `capture_mode`, `ChallengeHexagon` | Couverture ciblée |
| `max_points` | Points sur hexagones cibles | `ChallengeHexagon` | Intensité / répétition |
| `active_days` | Jours d'upload distincts | — | Régularité |
| `new_hexagons` | Nouveaux hexagones | (`geozone` optionnel) | Exploration |
| `distinct_zones` | Zones couvertes | `zone_admin_level`, `hexagons_per_zone` | Diversité géographique |
| `dataset_points` | Features collectées | `dataset` | Collecte de POI |
| `visit_hexagons` | Hexagones traversés (doublons inclus) | — | Volume de sorties |

## Récompenses

Chaque challenge peut définir des récompenses (`ChallengeReward`) attribuées
automatiquement à la fin du challenge aux participants ayant atteint un rang
suffisant (`rank_threshold`) :

| Type de récompense | Description |
|---|---|
| `badge` | Attribution d'un badge (identifié par `badge_id`) |
| `subscription_3m` | Abonnement premium de 3 mois |
| `subscription_6m` | Abonnement premium de 6 mois |
| `subscription_1y` | Abonnement premium de 1 an |
