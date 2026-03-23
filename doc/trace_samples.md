# Traces d'exemple (`trace_samples/`)

Convention de nommage :

```
closed_surface_<nb_surfaces>_hexagon_<nb_hexagons>.gpx
```

Le nom décrit le résultat attendu après import et extraction :
`nb_surfaces` surfaces fermées détectées, `nb_hexagons` hexagones attribués.

## Fichiers disponibles

| Fichier | Surfaces | Hexagones |
|---|---|---|
| `closed_surface_0_hexagon_0.gpx` | 0 | 0 |
| `closed_surface_1_hexagon_0.gpx` | 1 | 0 |
| `closed_surface_1_hexagon_20.gpx` | 1 | 20 |
| `closed_surface_1_hexagon_21.gpx` | 1 | 21 |
| `closed_surface_3_hexagon_14.gpx` | 3 | 14 |

## Utilisation dans les tests

### `traces/tests/test_upload.py`

Tests paramétrés (pytest) qui vérifient que chaque fixture produit le bon nombre de surfaces et d'hexagones après upload et extraction.

Fixtures utilisées : **toutes** (glob `closed_surface_*_hexagon_*.gpx`).

### `traces/tests/test_badge_award.py`

Tests unitaires (django.test.TestCase) de l'attribution automatique des badges.

| Fixture | Test | Badges attendus |
|---|---|---|
| `closed_surface_0_hexagon_0.gpx` | `test_open_trace_awards_one_badge` | `activite_premier_trace` |
| `closed_surface_1_hexagon_20.gpx` | `test_closed_trace_awards_multiple_badges` | `activite_premier_trace`, `territoire_premier`, `surfaces_geometre` |
