# Queues Procrastinate

Toutes les tâches asynchrones utilisent [Procrastinate](https://procrastinate.readthedocs.io/)
via `procrastinate.contrib.django`.

## Queues

| Queue | Description |
|---|---|
| `surface_extraction` | Extraction des surfaces fermées après upload |
| `badges` | Analyse de trace et attribution des badges |
| `challenges` | Scoring dataset, recalcul des leaderboards challenge |
| `tiles` | Génération de tuiles PNG (hexagons, scores, premium, par bbox) et recalcul des leaderboards globaux/zones |
| `emails` | Envoi d'emails (notification d'inscription) |

## Tâches par queue

### `surface_extraction`

| Tâche | Fichier | Description |
|---|---|---|
| `extract_surfaces` | `traces/tasks.py` | Extrait les surfaces fermées d'une trace |

### `badges`

| Tâche | Fichier | Description |
|---|---|---|
| `award_trace_badges` | `traces/tasks.py` | Analyse une trace et attribue les badges, puis dispatche les tâches suivantes (tiles, challenges, leaderboards) |

### `challenges`

| Tâche | Fichier | Description |
|---|---|---|
| `score_dataset_challenges_task` | `traces/tasks.py` | Score les challenges `dataset_points` après upload |
| `recompute_user_challenges` | `traces/tasks.py` | Recalcule les leaderboards des challenges actifs d'un utilisateur (hors `dataset_points`) |
| `compute_challenge_leaderboards` | `challenges/tasks.py` | Recalcule tous les leaderboards challenges actifs |
| `compute_single_challenge_leaderboard` | `challenges/tasks.py` | Recalcule le leaderboard d'un seul challenge |

### `tiles`

| Tâche | Fichier | Description |
|---|---|---|
| `recompute_leaderboard` | `traces/tasks.py` | Recalcule le leaderboard global (conquis/acquis) |
| `recompute_zone_leaderboard` | `traces/tasks.py` | Recalcule les leaderboards par zone géographique |
| `generate_tiles` | `traces/tasks.py` | Génère les tuiles hexagones pour une trace |
| `generate_score_tiles` | `traces/tasks.py` | Génère les tuiles scores pour une trace |
| `generate_user_tiles` | `traces/tasks.py` | Génère les tuiles premium pour un utilisateur |
| `regenerate_tiles_for_bbox` | `traces/tasks.py` | Régénère les tuiles hexagones dans une bbox |
| `regenerate_score_tiles_for_bbox` | `traces/tasks.py` | Régénère les tuiles scores dans une bbox |
| `regenerate_user_tiles_for_bbox` | `traces/tasks.py` | Régénère les tuiles premium dans une bbox |

### `emails`

| Tâche | Fichier | Description |
|---|---|---|
| `notify_new_registration` | `traces/tasks_emails.py` | Envoie un email de notification lors d'une nouvelle inscription |

## Lancement du worker

```bash
# Toutes les queues
python manage.py procrastinate worker --processes=1

# Une seule queue
python manage.py procrastinate worker --processes=1 --queues=badges
```
