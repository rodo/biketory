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

## Upload d'une trace GPX

### Endpoint

```
POST /api/upload/
```

### Headers

| Header | Valeur |
|---|---|
| `Authorization` | `Bearer <votre_token>` |
| `Content-Type` | `multipart/form-data` |

### Corps de la requête

| Champ | Type | Description |
|---|---|---|
| `gpx_file` | fichier | Fichier GPX à uploader |

### Réponse — succès

**HTTP 201 Created**

```json
{
  "id": 42,
  "extracted": true
}
```

| Champ | Description |
|---|---|
| `id` | Identifiant de la trace créée |
| `extracted` | `true` si les surfaces fermées ont été détectées |

### Réponses — erreurs

| Code | Exemple de corps | Cause |
|---|---|---|
| `400` | `{"error": "Missing gpx_file field."}` | Fichier absent |
| `400` | `{"error": "Trace too long (450 km). Maximum is 400 km."}` | Trace trop longue |
| `401` | `{"error": "Invalid or expired token."}` | Token invalide ou expiré |
| `429` | `{"error": "Daily upload limit reached.", "limit": 5, "next_slot": "2026-03-16T08:23:00+00:00"}` | Quota journalier atteint |

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
