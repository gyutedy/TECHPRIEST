# TECHPRIEST

Greffon OpenCode « drop-in » : un Tech-Prêtre qui développe, débogue et lance les rites du projet hôte, pilotable depuis Telegram via une sandbox Modal à la demande.

Statut : **tests locaux 12/12 OK** (exécutés le 2026-11-24). Les tests e2e réels (Telegram + Modal) restent **ATTENDU** : ils nécessitent tes propres secrets.

## Ce que c'est

Le greffon ajoute un agent principal `techpriest` et un sous-agent `servitor` à n'importe quel projet. Le projet hôte n'est pas restructuré : il reçoit la configuration OpenCode et un contrat `RITES.md` qui déclare ses commandes. Sans `RITES.md`, l'agent lit le code et le README mais refuse de lancer quoi que ce soit.

Le même code fonctionne en local (`cd projet && opencode`) et à distance (`opencode serve` + pont Telegram dans une sandbox Modal). Les actions `git push`, `gh workflow run` et `modal run` passent toujours par approbation.

## Arborescence

```
TECHPRIEST/
├── .opencode/
│   ├── opencode.jsonc
│   └── agents/
│       ├── techpriest.md
│       └── servitor.md
├── ops/
│   ├── techpriest_ops.py
│   ├── image.Dockerfile
│   ├── requirements.txt
│   ├── install.ps1
│   └── install.sh
├── tests/
│   └── test_plugin.py
├── MODELE_RITES.md
├── README.md
└── LICENSE
```

## Écart assumé au CDC

Le CDC affirme qu'un dossier `TECHPRIEST/` copié tel quel à la racine suffit. OpenCode ne découvre que les dossiers `.opencode/` situés entre le répertoire courant et la racine du projet : un `.opencode/` imbriqué dans `TECHPRIEST/` n'est pas vu quand on lance `opencode` depuis la racine hôte.

Le greffon livre donc `ops/install.ps1` et `ops/install.sh` : ils copient `.opencode/` à la racine du projet hôte et `MODELE_RITES.md` vers `RITES.md`. Rien du projet hôte n'est réécrit ; deux entrées sont ajoutées (`.opencode/` et `RITES.md`) au lieu d'une seule. C'est la condition nécessaire pour que l'affirmation (a) du CDC soit réellement vraie.

## Installation locale

Windows (PowerShell) :

```
powershell -ExecutionPolicy Bypass -File TECHPRIEST/ops/install.ps1 -Project <chemin-du-projet>
```

Linux / macOS :

```
bash TECHPRIEST/ops/install.sh <chemin-du-projet>
```

Ajouter `--force` (ou `-Force`) pour écraser des fichiers existants. Sans force, l'installateur affiche `SKIP` et laisse l'existant intact.

Puis remplir `RITES.md` à la racine du projet hôte :

```
Projet : <nom>
Installer :    <ex. pip install -r requirements.txt>
Lancer :       <ex. python main.py>
Tester :       <ex. pytest -q>
Déboguer :     <ex. logs dans logs/ ; mode verbeux : VERBOSE=1>
Jobs distants : <ex. gh workflow run build.yml ; modal run ops::app>
Interdits :    <ex. ne pas toucher à data/raw/>
```

Vérification : `cd <projet> && opencode`. L'agent `techpriest` s'ouvre par défaut avec le modèle `opencode/hy4-flash-free` (gratuit pour une durée limitée, politique de non-conservation des données). Pour changer de modèle, modifier une seule ligne : le champ `model` dans `.opencode/agents/techpriest.md` (et, si désiré, `model` dans `.opencode/opencode.jsonc`).

## Secrets — jamais dans le code

| Secret Modal | Contenu | Utilisé par |
| --- | --- | --- |
| `telegram-bot` | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_ID` | le pont Telegram dans la sandbox |
| `github-token` | `GITHUB_TOKEN` (scope `repo` + `workflow`) | clonage privé et CLI `gh` |
| `modal-token` | `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET` | la CLI `modal` pour relancer des runs |

Guide pas-à-pas pour obtenir ces valeurs : `GUIDE_SECRETS.md`.

Créer le bot avec `@BotFather` et récupérer son ID avec `@userinfobot`. Les secrets sont injectés par Modal dans l'environnement ; le dépôt ne contient aucune valeur littérale. Le test `Doctrine.test_no_literal_secret_values` vérifie cette règle à chaque exécution de la suite.

## Session distante

```
pip install -r ops/requirements.txt
modal setup
modal run ops/techpriest_ops.py::run_session --repo-url <url-du-projet>
```

La sandbox construit l'image (binaire OpenCode, Node 22, `gh`, CLI `modal`), clone le dépôt, lance `opencode serve --service`, récupère le mot de passe serveur via `opencode service get password`, puis démarre le pont `@grinev/opencode-telegram-bot`. Aucun port entrant : le bot parle au serveur local et à Telegram en polling sortant. La whitelist Telegram refuse tout utilisateur non autorisé.

Durée : `timeout=3600` s (1 h), `idle_timeout=600` s (10 min d'inactivité). Coût déduit : environ 0,19 $/session en configuration minimale, 0,38 $ en configuration confort — dans les 30 $/mois du plan Modal Starter.

## Tests

```
python -m unittest discover -s tests -v
```

Résultat réel de la dernière exécution locale : `Ran 12 tests ... OK`.

| # | Test | État |
| --- | --- | --- |
| T30 | Greffon copié dans un projet vierge | PASSÉ (structure, config JSON valide, agent par défaut) |
| T31 | Permissions | PASSÉ (statique : `ask` sur les trois commandes, `deny` sur `rm -rf`) |
| T32 | Sous-agent Serviteur | PASSÉ (statique : `edit`/`shell`/`subagent` refusés) |
| T33 | Pont sur hôte distant | ATTENDU (nécessite un token Telegram et un serveur réel) |
| T34 | Pont dans une sandbox Modal | ATTENDU (nécessite un compte Modal et le cold-start à mesurer) |
| T35 | Choix du modèle | PASSÉ (modèle unique, remplaçable en une ligne) |
| T36 | Budget session 1 h | PASSÉ (statique : bornes déclarées) ; mesure de consommation ATTENDU |
| T37 | Quota réel du run | ATTENDU (sortie réelle à produire) |
| T38 | Doctrine secrets | PASSÉ (aucune valeur littérale détectée) |
| T39 | Généricité | PASSÉ (copie simulée dans un projet sans rapport, empreintes inchangées) |

## Limites connues

- Le modèle gratuit peut être retiré à tout moment : une ligne à changer, ne pas laisser l'agent muet.
- Le mot de passe du serveur V2 est requis par le pont ; il est relu automatiquement au démarrage.
- Le cold-start Modal cible moins de 3 minutes ; ce seuil reste à mesurer en conditions réelles.
- GitHub Actions (déclencheurs PR/dispatch) reste optionnel et hors de ce greffon.

## Licence

MIT — voir `LICENSE`.
