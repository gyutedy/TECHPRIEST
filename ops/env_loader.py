import os

DEFAULT_KEYS = (
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ALLOWED_USER_ID",
    "GITHUB_TOKEN",
    "MODAL_TOKEN_ID",
    "MODAL_TOKEN_SECRET",
)


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env_file(root=None):
    base = root or repo_root()
    loaded = []
    for name in (".env", "env_techpriest"):
        path = os.path.join(base, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key, value = key.strip(), value.strip()
                    if key and value and not os.environ.get(key):
                        os.environ[key] = value
                        loaded.append(key)
        except OSError:
            continue
    return loaded


def missing_keys(keys=DEFAULT_KEYS):
    return [key for key in keys if not os.environ.get(key)]


def local_secret_values(keys=DEFAULT_KEYS):
    return {key: os.environ[key] for key in keys if os.environ.get(key)}
