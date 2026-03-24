# Landing page — carte interactive

## Vue d'ensemble

La landing page (`/`) affiche une carte Leaflet plein écran avec les hexagones
gagnés par tous les utilisateurs. Elle est publique (pas d'authentification
requise).

## Fichiers concernés

| Fichier | Rôle |
|---|---|
| `traces/views/landing.py` | Vues `landing` (page) et `landing_hexagons` (API JSON) |
| `traces/templates-light/traces/landing.html` | Template principal (thème light, prioritaire) |
| `traces/templates/traces/landing.html` | Template thème dark |
| `traces/urls.py` | Routes `/` et `/landing/hexagons/` |

**Attention :** le thème par défaut est `light` (`BIKETORY_THEME`). Le dossier
`templates-light/` est prioritaire sur `templates/` grâce à la configuration
`_THEME_DIRS` dans `settings.py`.

## Position initiale de la carte

Priorité de la position initiale :

1. **Cookie `map_pos`** — position et zoom sauvegardés lors de la dernière visite
   (format : `lat,lng,zoom`, durée : 1 an)
2. **Dernier hexagone gagné** — si l'utilisateur n'est pas connecté et qu'il
   n'a pas de cookie, la carte se centre sur le centroïde du `HexagonScore`
   le plus récent (`last_earned_at`) au **zoom 14**
3. **Fallback** — `[0, 0]` zoom 2

La position initiale est calculée côté serveur dans la vue `landing` et passée
au template via la variable `last_center` (JSON `[lat, lng]` ou `null`).

## Chargement des hexagones

### Zoom minimum

Les hexagones ne s'affichent qu'à partir du **zoom 11** (`MIN_HEX_ZOOM`).
En dessous, aucune requête n'est envoyée et la layer est retirée de la carte.

### Bbox élargie

La requête à `/landing/hexagons/` inclut un paramètre `bbox` calculé à partir
de la vue courante, élargie d'un facteur **0.2× la taille de la vue** de chaque
côté (padding = 0.2). Cela couvre environ 2× la surface visible pour charger
des hexagones légèrement au-delà des bords.

### Cycle de vie

À chaque déplacement ou changement de zoom (`moveend`) :

1. **Annulation** du fetch en cours via `AbortController`
2. **Suppression** de la layer hexagones existante (`map.removeLayer`)
3. Si zoom >= 12 : nouveau fetch avec bbox élargie, création d'un `L.geoJSON`
   vide ajouté à la carte, puis ajout progressif des features par lots de 50
   via `requestAnimationFrame` (affichage graduel)
4. Si zoom < 12 : arrêt (pas de requête)

L'`AbortController` empêche une réponse tardive d'ajouter des hexagones à un
niveau de zoom où ils ne devraient pas apparaître (race condition).

## API `/landing/hexagons/`

Endpoint GET retournant du JSON :

```json
{
  "geojson": { "type": "FeatureCollection", "features": [...] },
  "current_user": "username" | null,
  "friend_usernames": ["ami1", "ami2"]
}
```

Chaque feature contient :
- `hexagon_id` — PK de l'hexagone
- `username` — propriétaire du score
- `points` — score
- `is_friend` — booléen

Le paramètre `bbox` (optionnel) filtre les hexagones avec `bboverlaps`.
Sans bbox, tous les hexagones sont retournés.

## Couleurs des hexagones (thème light)

### Hexagones de l'utilisateur connecté (dégradé bleu)

| Points | Couleur |
|---|---|
| >= 10 | `#1a4971` |
| >= 5 | `#1f6199` |
| >= 2 | `#3a94cc` |
| < 2 | `#6bb5e0` |

### Hexagones des autres (dégradé vert-gris)

| Points | Couleur |
|---|---|
| >= 10 | `#4a5e4c` |
| >= 5 | `#6b7d6c` |
| >= 2 | `#8a9e8b` |
| < 2 | `#b0bfb1` |

### Hexagones des amis

Chaque ami reçoit une couleur unique depuis `FRIEND_PALETTE` (12 couleurs).

## Popup au clic

Un clic sur un hexagone ouvre une popup affichant d'abord un résumé rapide :

- **Utilisateur connecté** : `username · 12pt`
- **Visiteur non connecté** : `12pt` (pas de nom affiché)

Puis les scores détaillés sont chargés via `/hexagons/<pk>/` et remplacent le
contenu initial (tableau utilisateur / points / dernière activité).

Il n'y a pas de tooltip au hover.

## Calques (menu « Calques »)

Le menu dans la barre supérieure permet de masquer/afficher :

- **Mes hexagons** (utilisateur connecté uniquement)
- **Autres utilisateurs**
- **Amis** — toggle global + toggle individuel par ami

La visibilité est gérée via un `Set` de catégories masquées et modification du
style (opacity à 0).

## Graticule

Des lignes pointillées représentent les méridiens et parallèles aux degrés
entiers. Elles sont redessinées à chaque déplacement de la carte (`moveend`).

## Zoom display

Le niveau de zoom actuel est affiché dans la barre supérieure et mis à jour à
chaque `zoomend`.
