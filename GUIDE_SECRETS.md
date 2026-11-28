# Guide des secrets — TECHPRIEST

Trois secrets Modal sont **obligatoires** : le code les déclare avec `modal.Secret.from_name(...)`, donc un secret absent fait échouer le lancement, même si tu n'utilises pas toutes les valeurs.

| Secret Modal (nom exact) | Clés qu'il contient | Où les obtenir |
| --- | --- | --- |
| `telegram-bot` | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_ID` | @BotFather et @userinfobot |
| `github-token` | `GITHUB_TOKEN` | GitHub → Paramètres → Jetons d'accès personnels |
| `modal-token` | `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET` | `modal token new` ou réglages du workspace Modal |

Les noms de secrets sont sensibles à la casse et doivent être exactement ceux du tableau. Les noms de clés aussi.

## Pré-requis

```
pip install modal
modal setup
```

Cela ouvre le navigateur et écrit tes identifiants dans `~/.modal.toml`. Vérifie avec `modal secret list`.

## 1. Telegram → secret `telegram-bot`

1. Ouvre `@BotFather` dans Telegram et envoie `/newbot`.
2. Donne un nom public, puis un nom d'utilisateur se terminant par `bot`.
3. Copie le token renvoyé. Il ressemble à `<chiffres>:<lettres_et_tirets>`.
4. Ouvre `@userinfobot`, envoie-lui un message : il te répond avec ton **ID numérique**. C'est ton ID d'utilisateur Telegram, pas l'ID du bot. Cet ID est la whitelist : toute autre personne sera refusée.
5. Si tu veux utiliser le bot dans un groupe, envoie `/setprivacy` à @BotFather et choisis `Disable` pour ce bot. En chat privé ce n'est pas nécessaire.
6. Crée le secret :

```
modal secret create telegram-bot TELEGRAM_BOT_TOKEN=<colle_le_token_du_bot> TELEGRAM_ALLOWED_USER_ID=<ton_id_numerique>
```

Alternative dans le dashboard : Settings → Secrets → New secret, nom `telegram-bot`, puis les deux clés ci-dessus.

Note : le mot de passe du serveur OpenCode V2 n'est **pas** à mettre ici. `ops/techpriest_ops.py` le récupère automatiquement avec `opencode service get password` au démarrage.

## 2. GitHub → secret `github-token`

Le token sert au clonage des dépôts privés et à `gh workflow run`.

**Jeton classique (le plus simple, conforme au CDC) :**

1. GitHub → avatar en haut à droite → `Settings`.
2. `Developer settings` → `Personal access tokens` → `Tokens (classic)`.
3. `Generate new token (classic)`, donne un nom, choisis une expiration (90 jours par exemple).
4. Coche exactement ces scopes : `repo` (dépôts privés) et `workflow` (déclenchement des Actions).
5. `Generate token`, copie la valeur tout de suite (elle n'est affichée qu'une fois).

**Alternative fine-grained :** donner à au moins un dépôt les permissions `Contents: read`, `Actions: write` et `Metadata: read`.

6. Crée le secret :

```
modal secret create github-token GITHUB_TOKEN=<colle_le_pat>
```

Si tu n'utilises que des dépôts publics et aucun `gh workflow run`, ce secret peut contenir une valeur factice, mais il doit exister.

## 3. Modal → secret `modal-token`

Ce secret permet à la CLI `modal` **dans la sandbox** de relancer des runs (`modal run`) à la demande de l'agent.

1. Sur ta machine, lance `modal token new` et valide dans le navigateur.
2. Lis `~/.modal.toml` :

```
Get-Content "$env:USERPROFILE\.modal.toml"
```

Tu y trouves `token_id = "ak-..."` et `token_secret = "as-..."`. Ce sont respectivement `MODAL_TOKEN_ID` et `MODAL_TOKEN_SECRET`.

3. Crée le secret :

```
modal secret create modal-token MODAL_TOKEN_ID=<ak-...> MODAL_TOKEN_SECRET=<as-...>
```

Alternative : dashboard Modal → Settings → Tokens → créer un token, ou `Service Users` pour un workspace partagé. La valeur du secret n'est montrée qu'une fois à la création.

## Vérification

```
modal secret list
python -m unittest discover -s tests -v
modal run ops/techpriest_ops.py::run_session --repo-url <url-du-projet>
```

`modal secret list` doit afficher exactement `telegram-bot`, `github-token` et `modal-token`. La suite de tests vérifie qu'aucune valeur littérale n'a été collée dans le code.

## Règles d'or

- Ne jamais mettre ces valeurs dans un fichier du dépôt, un prompt ou un log.
- Remplacer un token compromis immédiatement : BotFather `/revoke` pour Telegram, suppression du PAT pour GitHub, rotation du token Modal.
- Le token GitHub collé dans le chat lors de la création du dépôt doit être révoqué : il a servi une seule fois à créer le repo et à pousser le commit initial.
- La whitelist Telegram (`TELEGRAM_ALLOWED_USER_ID`) est la première ligne de défense ; ne la désactive pas.
