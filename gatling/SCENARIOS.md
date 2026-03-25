# Scénarios Gatling

Ce document liste tous les scénarios de performance Gatling du projet.
**Il doit être mis à jour** à chaque ajout, modification ou suppression de scénario.

## Lancement

```bash
cd gatling
mvn gatling:test -Dgatling.simulationClass=biketory.<NomSimulation> -DbaseUrl=http://localhost:8000
```

## Scénarios

### PublicBrowsingSimulation

**Fichier :** `src/main/java/biketory/PublicBrowsingSimulation.java`

Navigation anonyme sur les pages publiques du site. Un seul utilisateur parcourt
séquentiellement tous les endpoints publics avec des pauses de 1 à 3 secondes.

**Étapes :**

1. `GET /` — Landing page
2. `GET /api/hexagons/` — API hexagons
3. `GET /api/hexagons/?bbox=-2,46,4,49` — API hexagons avec bbox
4. `GET /legal/` — Mentions légales
5. `GET /stats/` — Stats par utilisateur
6. `GET /stats/monthly/` — Stats mensuelles
7. `GET /stats/pie/` — Répartition
8. `GET /stats/badges/` — Badges

**Injection :** `atOnceUsers(1)`
**Assertions :** p95 < 2s, succès > 95 %

---

### RegistrationSimulation

**Fichier :** `src/main/java/biketory/RegistrationSimulation.java`

Création de comptes en masse avec des identifiants générés aléatoirement (UUID).
Chaque utilisateur virtuel récupère le formulaire d'inscription, extrait le token
CSRF, puis soumet le formulaire.

**Étapes :**

1. `GET /register/` — Récupération du formulaire et du token CSRF
2. `POST /register/` — Soumission (username, email, password1, password2)

**Injection :** `atOnceUsers(2)`
**Assertions :** p95 < 2s, succès > 95 %

---

### UploadAndStatsSimulation

**Fichier :** `src/main/java/biketory/UploadAndStatsSimulation.java`

Scénario complet en deux phases séquentielles (`andThen`) : upload de traces GPX
par deux utilisateurs distincts, puis vérification des statistiques d'hexagons.

Les identifiants sont générés avec un préfixe unique par exécution (`perf_<uuid>_u1`,
`perf_<uuid>_u2`) pour éviter les collisions.

**Fixtures GPX :** `src/main/resources/user1_hexagons_12.gpx` et `user2_hexagons_10.gpx`
(copies de `gatling/traces/`)

#### Phase 1 — Upload traces (2 utilisateurs en parallèle)

Chaque utilisateur exécute :

1. `GET /register/` + `POST /register/` — Création de compte
2. `GET /accounts/login/` + `POST /accounts/login/` — Connexion
3. `GET /upload/` + `POST /upload/` — Upload du fichier GPX (multipart)
4. `GET /traces/<pk>/` — Consultation du détail de la trace

| Utilisateur | Fichier GPX | Hexagons attendus |
|---|---|---|
| user 1 | `user1_hexagons_12.gpx` | 12 |
| user 2 | `user2_hexagons_10.gpx` | 10 |

#### Phase 2 — Vérification des stats (1 utilisateur)

1. `GET /stats/pie/` — Récupération de la page de répartition
2. Extraction du JSON `const ALL = {...}` depuis le body HTML
3. Vérification que chaque utilisateur a le bon nombre d'hexagons

**Injection :** `atOnceUsers(2)` puis `atOnceUsers(1)`
**Assertions :** p95 < 5s, succès > 95 %
