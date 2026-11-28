# Guide des secrets — TECHPRIEST (système PARI)

TECHPRIEST utilise le même modèle que le monde PARI : un fichier plat local `env_techpriest`, gitignoré, jamais versionné. Aucun secret n'est stocké dans le dashboard Modal ni dans GitHub.

## Règle de fonctionnement

1. Copier `env_techpriest.example` vers `env_techpriest` à la racine du dépôt.
2. Remplir les valeurs, une par ligne sous la forme `CLE=valeur`. Les lignes vides et celles commençant par `#` sont ignorées.
3. Le fichier est listé dans `.gitignore` : `git status` ne l'affiche pas et `git push` ne l'envoie pas.
4. Au `modal run`, `ops/env_loader.py` lit le fichier puis transmet les valeurs à la sandbox avec `modal.Secret.from_dict(...)`. Rien n'est écrit dans l'image, dans un Volume ou dans un fichier du dépôt.
5. Une variable déjà présente dans l'environnement n'est jamais écrasée (même règle que `load_env_pari()` dans `workflow.py` de PARI). `.env` est lu avant `env_techpriest`.

| Clé | Où l'obtenir |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | @BotFather → `/newbot` |
| `TELEGRAM_ALLOWED_USER_ID` | @userinfobot (ton ID numérique) |
| `GITHUB_TOKEN` | GitHub → Settings → Developer settings → Personal access tokens |
| `MODAL_TOKEN_ID` | `modal token new`, champ `token_id` dans `~/.modal.toml` |
| `MODAL_TOKEN_SECRET` | `modal token new`, champ `token_secret` dans `~/.modal.toml` |

## 1. Telegram

1. Ouvre `@BotFather` dans Telegram et envoie `/newbot`.
2. Donne un nom public, puis un nom d'utilisateur se terminant par `bot`.
3. Copie le token renvoyé dans `env_techpriest` sous `TELEGRAM_BOT_TOKEN=`.
4. Ouvre `@userinfobot`, envoie-lui un message : il te répond avec ton **ID numérique**. Mets-le dans `TELEGRAM_ALLOWED_USER_ID=`. Cet ID est la whitelist : toute autre personne est refusée.
5. Pour un groupe, envoie `/setprivacy` à @BotFather et choisis `Disable`. En chat privé, inutile.

Aucun mot de passe serveur n'est à mettre dans le fichier : le pont tourne en mode V1 (`opencode serve --port 4096`), où le mot de passe est optionnel.

## 2. GitHub

Le token sert au clonage des dépôts privés et à `gh workflow run`.

1. GitHub → avatar → `Settings` → `Developer settings` → `Personal access tokens` → `Tokens (classic)`.
2. `Generate new token (classic)`, donne un nom et une expiration, coche `repo` et `workflow`, puis `Generate token`.
3. Copie la valeur dans `GITHUB_TOKEN=` de `env_techpriest`.

Alternative fine-grained : permissions `Contents: read`, `Actions: write`, `Metadata: read`. Pour un dépôt public sans `gh workflow run`, une valeur factice suffit.

## 3. Modal

1. Sur ta machine : `pip install modal` puis `modal token new`, et valide dans le navigateur.
2. Lis `~/.modal.toml` avec `Get-Content "$env:USERPROFILE\.modal.toml"`.
3. Copie `token_id` dans `MODAL_TOKEN_ID=` et `token_secret` dans `MODAL_TOKEN_SECRET=`.

Ces valeurs permettent à la CLI `modal` dans la sandbox de relancer des runs à la demande.

## Vérification

```
python -m unittest discover -s tests -v
modal run ops/techpriest_ops.py::run_session --repo-url <url-du-projet>
```

Si une clé manque, le lancement affiche `[env_techpriest] cles manquantes : ...` avec les noms seulement, jamais les valeurs.

## Règles d'or

- Ne jamais committer `env_techpriest`, ni coller ses valeurs dans un prompt, un log ou un fichier du dépôt.
- Le dépôt étant public, un fichier d'environnement versionné exposerait immédiatement les clés.
- Ces clés sont temporaires : révoque-les après usage (BotFather `/revoke`, suppression du PAT GitHub, rotation du token Modal).
- Le token GitHub collé dans le chat lors de la création du dépôt doit être révoqué : il a servi une seule fois au repo et au commit initial.
- La whitelist Telegram (`TELEGRAM_ALLOWED_USER_ID`) est la première ligne de défense ; ne la désactive pas.
