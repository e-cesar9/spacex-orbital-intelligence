# CODE_QUALITY.md — Standards de code (niveau senior / staff)

Objectif : définir ce qu’on appelle un **code de haut niveau** :
lisible, testable, maintenable, robuste en production, sécurisé,
observable, performant — et **pilotable par un agent de coding**.

Ce document contient des règles **vérifiables**
(review / CI / tests / linters / règles d’architecture),
pas des opinions.

---

## 0) Principes de décision (priorités globales)

En cas d’arbitrage ou d’incertitude, l’ordre de priorité est :

1. **Sécurité**
2. **Correction fonctionnelle**
3. **Robustesse / résilience**
4. **Lisibilité / maintenabilité**
5. **Performance**

Règles par défaut :
- Refuser est préférable à accepter silencieusement
- Toute entrée externe est hostile
- Toute dépendance externe peut tomber
- Toute optimisation doit être mesurée ou justifiée

Toute exception à ces principes doit être **explicitement documentée**.

---

## 1) Principes de conception

### 1.1 Lisibilité > cleverness
- Le code doit être compris rapidement par un·e autre dev.
- Les noms expriment l’intention, pas l’implémentation.
- Pas de logique cachée dans des helpers “magiques”.

### 1.2 Simplicité, localité, séparation
- Minimiser le nombre d’états possibles.
- Minimiser les chemins d’exécution.
- Isoler le domaine de toute technologie (HTTP, ORM, broker).

---

## 2) Architecture & dépendances

### 2.1 Frontières claires (DIP / SRP)

- Le **domaine** ne dépend jamais de l’infrastructure.
- L’infrastructure implémente des interfaces définies côté domaine.
- Les adapters (DB, HTTP, cache, broker) sont interchangeables.

**Règles enforceables**
- Interdiction d’imports cross-layer / cross-domain (lint/boundaries).
- Les modèles ORM ne sortent jamais de la couche infra.
- Mapping explicite vers DTO / objets domaine.

---

### 2.2 Modèle de domaine (obligatoire)

- Le domaine est **immuable par défaut**.
- Pas de setters publics sur les entités métier.
- Les invariants métier sont garantis :
  - à la construction
  - ou via des méthodes métier explicites
- Validation métier ≠ validation d’entrée.

**Règles**
- Impossible de créer un objet métier invalide.
- Les règles métier ne dépendent pas du transport (HTTP/event).

---

### 2.3 Contrats

- API synchrones versionnées (OpenAPI / Proto).
- Events asynchrones versionnés (JSON Schema / Avro / Proto).
- Toute rupture de contrat est explicite et documentée.

---

## 3) Validation, sérialisation et sécurité des entrées

### 3.1 Validation à la frontière (obligatoire)

Toute entrée externe est validée :
HTTP, events, CLI, fichiers, jobs.

**Règles**
- Allowlist stricte : champs inconnus refusés.
- Validation des tailles, formats, enums, ranges.
- Normalisation explicite (trim, casing, unicode).

---

### 3.2 Protection contre injections (SQL / NoSQL / Command)

- **Jamais** de concaténation de chaînes dans une requête.
- Requêtes paramétrées ou ORM correctement utilisés.

**Règles**
- Interdiction de `"... WHERE id=" + input`.
- Toute requête dynamique est :
  - revue explicitement
  - couverte par des tests ciblés.

---

### 3.3 XSS / Injection HTML

- Échappement par défaut.
- `dangerouslySetInnerHTML` interdit sans sanitization stricte.
- Sanitizer en allowlist (jamais blacklist).

---

### 3.4 SSRF (appels sortants)

- Blocage des IP internes et metadata cloud
  (`169.254.169.254`, ranges privés, loopback).
- Allowlist de domaines autorisés.
- Timeouts obligatoires (connect + read).

---

### 3.5 Upload et parsing de fichiers (PDF / CSV / XLS / XLSX)

**Menaces**
- Zip bombs / decompression bombs
- DoS mémoire / CPU
- CSV / Excel formula injection
- Macros (XLSM)
- MIME spoofing

**Règles**
- Vérifier **type réel (magic bytes)** + MIME + extension.
- Taille max stricte (ex : 10–20 MB).
- Limites de lignes / cellules.
- Interdiction des macros (`xlsm` refusé).
- Parsing en streaming si possible.
- Timeout de parsing.
- Neutralisation des formules à l’export (`=`, `+`, `-`, `@`).

---

## 4) Appels API sortants (robustesse)

### 4.1 Timeouts & budgets

- Tout appel réseau a un timeout explicite.
- Budget global par requête (éviter cascades).

---

### 4.2 Retries contrôlés

- Retries uniquement sur erreurs transitoires.
- Backoff + jitter.
- Nombre max de retries.
- Circuit breaker si nécessaire.

**Interdictions**
- Retry sur erreurs métier.
- Retry sur opérations non idempotentes sans idempotency key.

---

### 4.3 Idempotency

- Endpoints sensibles acceptent une `Idempotency-Key`.
- Déduplication côté serveur (clé + résultat).
- Comportement documenté.

---

### 4.4 Concurrence et fan-out

- Parallélisation limitée (pool).
- Pas de fan-out non borné.
- Protection contre DDoS involontaire.

---

## 5) Cohérence des données & concurrence

- Les garanties métier critiques reposent aussi sur la base :
  - contraintes UNIQUE
  - clés étrangères
  - transactions
- Gestion explicite des race conditions.

**Règles**
- Pas de confiance exclusive dans un check applicatif.
- Usage explicite d’optimistic locking / versioning si nécessaire.
- Transactions courtes.

---

## 6) Throttling / Rate limiting

### 6.1 Entrant

- Par IP / user / API key.
- Endpoints sensibles différenciés.

**Règles**
- HTTP 429 + `Retry-After`.
- Burst + sustained quotas.

---

### 6.2 Sortant

- Limites par provider.
- Bulkhead / queue pour isolation des pannes.

---

## 7) Cache

### 7.1 Quand cacher

- Lecture fréquente, coût élevé.
- Staleness acceptable et connue.

---

### 7.2 Stratégies

- TTL simple
- Cache-aside
- Stale-while-revalidate
- Invalidation par event

---

### 7.3 Sécurité cache

- Pas de données privées dans un cache partagé sans clé stricte.
- Clés incluant user / tenant / permissions.
- Protection contre cache poisoning.

---

### 7.4 Anti-patterns

- TTL arbitraire sans justification.
- Cache d’erreurs non distinguées.
- Double cache non documenté.

---

## 8) Gestion des erreurs & sémantique d’échec

- Erreurs typées :
  - métier
  - techniques
- Mapping explicite vers HTTP / events.
- Pas de `catch (Exception) { log; return null }`.

**Règles**
- Les erreurs métier ne déclenchent jamais de retry.
- Les erreurs techniques sont :
  - loggées
  - métriquées
  - corrélées (`request_id`).
- Aucune erreur critique n’est silencieuse.

---

## 9) Performance

### 9.1 Principes

- Optimiser après mesure.
- Réduire IO avant CPU.

---

### 9.2 Base de données

- Index sur chemins critiques.
- Pagination correcte (keyset si volume élevé).
- Détection du N+1.
- Transactions courtes.

---

### 9.3 Frontend

- Code splitting.
- Lazy loading.
- Éviter rerenders inutiles.
- Cache client cohérent.

---

## 10) Sécurité applicative

### 10.1 AuthN / AuthZ

- Séparation AuthN / AuthZ.
- RBAC / ABAC explicites.
- Contrôles serveur obligatoires.

---

### 10.2 Secrets

- Jamais en git.
- Rotation régulière.
- Scopes minimaux.

---

### 10.3 Dépendances

- Audit régulier.
- Scanner SCA en CI.

---

### 10.4 Logs

- Pas de secrets / tokens / PII sensibles.
- Logs structurés.
- `request_id` obligatoire.

---

## 11) Observabilité & incident response

- Logs structurés.
- Metrics : latence, erreurs, saturation, queues.
- Tracing distribué si multi-services.
- Healthchecks liveness / readiness.
- Runbook minimal.

---

## 12) Tests & qualité

### 12.1 Pyramide

- Unit (domaine) majoritaires.
- Integration ciblés.
- Contract tests si nécessaire.
- Peu de E2E.

---

### 12.2 Sécurité & perf (minimum)

- Tests injection.
- Tests upload limites.
- Tests rate limiting.
- Smoke perf sur endpoints critiques.

---

## 13) Tooling & CI (non négociable)

CI bloque si :
- Lint / format / typecheck KO
- Tests KO
- Violations d’architecture
- Imports cross-layer
- Appels réseau sans timeout
- (Optionnel mais recommandé) audit deps KO

Pré-commit :
- lint + format sur fichiers modifiés.

---

## 14) Checklist de review

### Sécurité
- [ ] Inputs validés (allowlist, tailles)
- [ ] Pas de concat SQL
- [ ] Upload sécurisé
- [ ] SSRF protégé
- [ ] Logs sans secrets

### Robustesse IO
- [ ] Timeouts partout
- [ ] Retries contrôlés
- [ ] Idempotency
- [ ] Throttling sortant

### Données
- [ ] Pas de race condition
- [ ] Contraintes DB présentes

### Performance
- [ ] Pas de N+1
- [ ] Pagination correcte
- [ ] Cache justifié

### Qualité
- [ ] Domaine clair et immuable
- [ ] Tests métier + edge cases
- [ ] Observabilité minimale
