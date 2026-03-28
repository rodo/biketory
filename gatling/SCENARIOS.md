# Scénarios Gatling

Ce document liste tous les scénarios de performance Gatling du projet.
**Il doit être mis à jour** à chaque ajout, modification ou suppression de scénario.

## Architecture

```
BaseSimulation (abstraite)
├── PublicBrowsingSimulation    — navigation publique
├── StatsApiSimulation          — endpoints API stats JSON
├── RegistrationSimulation      — création de comptes
├── UploadAndStatsSimulation    — upload GPX + vérification hexagons
└── AllSimulation               — enchaîne les 4 scénarios ci-dessus
```

`BaseSimulation` centralise toute la logique partagée : configuration HTTP,
feeders (`registrationFeeder`, `uploadFeeder`), chains réutilisables
(`register()`, `login()`, `uploadGpx()`, `fetchCsrf()`) et factory methods
de scénarios (`publicBrowsingScenario()`, `statsApiScenario()`,
`registrationScenario()`, `uploadScenario()`, `verifyStatsScenario()`).

Les sous-classes ne contiennent que le `setUp()` avec injection et assertions.

## Lancement

```bash
cd gatling

# Un scénario individuel
mvn gatling:test -Dgatling.simulationClass=biketory.<NomSimulation> -DbaseUrl=http://localhost:8000

# Tous les scénarios (CI)
mvn gatling:test -Dgatling.simulationClass=biketory.AllSimulation -DbaseUrl=http://localhost:8000
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
4. `GET /about/` — À propos
5. `GET /legal/` — Mentions légales
6. `GET /stats/` — Stats par utilisateur
7. `GET /stats/monthly/` — Stats mensuelles
8. `GET /stats/pie/` — Répartition
9. `GET /stats/badges/` — Badges

**Injection :** `atOnceUsers(1)`
**Assertions :** p95 < 2s, succès > 95 %

---

### StatsApiSimulation

**Fichier :** `src/main/java/biketory/StatsApiSimulation.java`

Test des 3 endpoints API JSON qui fournissent les données aux graphiques Chart.js.
Un seul utilisateur appelle séquentiellement chaque endpoint et vérifie que la réponse
contient les clés `labels` et `datasets`.

**Étapes :**

1. `GET /api/stats/monthly/` — Hexagons acquis par mois
2. `GET /api/stats/traces/` — Traces uploadées par mois
3. `GET /api/stats/users/` — Hexagons gagnés par utilisateur par mois

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

---

### AllSimulation

**Fichier :** `src/main/java/biketory/AllSimulation.java`

Enchaîne séquentiellement les 4 scénarios ci-dessus via `andThen()`.
C'est la simulation à utiliser en CI pour tout valider en une seule étape.

**Ordre d'exécution :**

1. PublicBrowsing — `atOnceUsers(1)`
2. API Stats — `atOnceUsers(1)`
3. Registration — `atOnceUsers(2)`
4. Upload — `atOnceUsers(2)` puis Verify stats — `atOnceUsers(1)`

**Assertions :** p95 < 5s, succès > 95 %
