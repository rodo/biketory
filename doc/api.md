# API Biketory

## Authentification

L'API utilise des tokens Bearer. Chaque token est valide **31 jours** à compter de sa génération.

### Générer un token

1. Connectez-vous à Biketory
2. Rendez-vous sur votre page de profil (`/profile/`)
3. Dans la section **Token API**, cliquez sur **Générer**
4. Copiez le token affiché — il ne sera plus affiché en clair après rechargement

> Régénérer un token révoque immédiatement l'ancien.

---

## Endpoints

### Upload d'une trace GPX

```
POST /api/upload/
```

**Authentification :** Bearer token (Premium requis)

**Headers**

| Header | Valeur |
|---|---|
| `Authorization` | `Bearer <votre_token>` |
| `Content-Type` | `multipart/form-data` |

**Corps de la requête**

| Champ | Type | Description |
|---|---|---|
| `gpx_file` | fichier | Fichier GPX à uploader |

**Réponse — succès (201)**

```json
{
  "id": 42,
  "uuid": "550e8400-e29b-41d4-a716-446655440000"
}
```

| Champ | Description |
|---|---|
| `id` | Identifiant numérique de la trace créée |
| `uuid` | Identifiant UUID de la trace |

**Réponses — erreurs**

| Code | Exemple de corps | Cause |
|---|---|---|
| `400` | `{"error": "Missing gpx_file field."}` | Fichier absent |
| `400` | `{"error": "Trace too long (450 km). Maximum is 400 km."}` | Trace trop longue |
| `401` | `{"error": "Invalid or expired token."}` | Token invalide ou expiré |
| `403` | `{"error": "API access requires an active Premium subscription."}` | Utilisateur non Premium |
| `429` | `{"error": "Daily upload limit reached.", "limit": 5, "next_slot": "2026-03-16T08:23:00+00:00"}` | Quota journalier atteint |

---

### Statut d'une trace

```
GET /api/traces/<uuid>/status/
```

**Authentification :** aucune

**Paramètre URL**

| Paramètre | Description |
|---|---|
| `uuid` | UUID de la trace |

**Réponse — succès (200)**

```json
{
  "status": "analyzed"
}
```

| Valeur | Description |
|---|---|
| `not_analyzed` | La trace n'a pas encore été analysée |
| `analyzed` | L'analyse est terminée |

**Réponse — erreur**

| Code | Corps | Cause |
|---|---|---|
| `404` | `{"error": "not found"}` | Trace introuvable |

---

### Hexagones dynamiques (landing)

```
GET /api/hexagons/
```

**Authentification :** aucune (le contenu varie selon l'état de connexion)

**Paramètres query**

| Paramètre | Type | Description |
|---|---|---|
| `bbox` | string | `"west,south,east,north"` — filtre les hexagones dont la bounding box chevauche le rectangle |

**Réponse — succès (200)**

```json
{
  "geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": { "type": "Polygon", "coordinates": [...] },
        "properties": {
          "hexagon_id": 7,
          "username": "alice",
          "points": 3,
          "is_friend": true
        }
      }
    ]
  },
  "current_user": "alice",
  "friend_usernames": ["bob", "charlie"]
}
```

| Champ | Description |
|---|---|
| `geojson` | FeatureCollection des hexagones avec scores |
| `current_user` | Username de l'utilisateur connecté, `null` si anonyme |
| `friend_usernames` | Liste triée des usernames amis |

> La visibilité des hexagones dépend des settings `LANDING_SHOW_OWN_DYNAMIC_HEXAGONS` et `LANDING_SHOW_OTHER_DYNAMIC_HEXAGONS`.

---

### Statistiques mensuelles (hexagones)

```
GET /api/stats/monthly/
```

**Authentification :** aucune

**Réponse — succès (200)**

```json
{
  "labels": ["2024-01", "2024-02", "2024-03"],
  "datasets": [
    {
      "label": "Hexagons acquired",
      "data": [42, 55, 38],
      "backgroundColor": "#2980b9"
    },
    {
      "label": "New hexagons",
      "data": [10, 12, 8],
      "backgroundColor": "#27ae60"
    }
  ]
}
```

Retourne `{"labels": [], "datasets": []}` si aucune donnée.

---

### Statistiques mensuelles (traces)

```
GET /api/stats/traces/
```

**Authentification :** aucune

**Réponse — succès (200)**

```json
{
  "labels": ["2024-01", "2024-02", "2024-03"],
  "datasets": [
    {
      "label": "Traces",
      "data": [5, 8, 12],
      "backgroundColor": "#e74c3c"
    }
  ]
}
```

Retourne `{"labels": [], "datasets": []}` si aucune donnée.

---

### Détail d'un hexagone

```
GET /hexagons/<pk>/
```

**Authentification :** aucune

**Paramètre URL**

| Paramètre | Description |
|---|---|
| `pk` | Identifiant numérique de l'hexagone |

**Réponse — succès (200)**

```json
{
  "scores": [
    {
      "username": "alice",
      "points": 5,
      "last_earned_at": "2024-03-15 14:32"
    }
  ]
}
```

Retourne les 10 meilleurs scores pour cet hexagone, triés par `last_earned_at` décroissant.

**Réponse — erreur**

| Code | Cause |
|---|---|
| `404` | Hexagone introuvable |

---

## Exemples

### curl

```bash
curl -X POST https://biketory.example.com/api/upload/ \
  -H "Authorization: Bearer <votre_token>" \
  -F "gpx_file=@mon_trajet.gpx"
```

### Python (requests)

```python
import requests

TOKEN = "<votre_token>"
GPX_PATH = "mon_trajet.gpx"

with open(GPX_PATH, "rb") as f:
    response = requests.post(
        "https://biketory.example.com/api/upload/",
        headers={"Authorization": f"Bearer {TOKEN}"},
        files={"gpx_file": f},
    )

print(response.status_code, response.json())
```

### JavaScript (fetch)

```js
const token = "<votre_token>";
const file = document.querySelector('input[type="file"]').files[0];

const form = new FormData();
form.append("gpx_file", file);

const res = await fetch("/api/upload/", {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
  body: form,
});

console.log(await res.json());
```

---

## Limites

- Longueur maximale d'une trace : **400 km**
- Quota journalier : **5 uploads** par tranche de 24 h (configurable par l'administrateur)
- Durée de validité d'un token : **31 jours**
