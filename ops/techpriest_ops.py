import os
import subprocess
import sys
import time

import modal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from env_loader import load_env_file, local_secret_values, missing_keys

APP_NAME = "techpriest-ops"
SESSION_SECONDS = 3600
IDLE_SECONDS = 600
STARTUP_GRACE_SECONDS = 180
BRIDGE_PACKAGE = "@grinev/opencode-telegram-bot@latest"

app = modal.App(APP_NAME)

if modal.is_local():
    load_env_file()
    absent = missing_keys()
    if absent:
        print("[env_techpriest] cles manquantes : " + ", ".join(absent), file=sys.stderr)
    runtime_secret = modal.Secret.from_dict(local_secret_values())
else:
    runtime_secret = modal.Secret.from_dict({})

OPS_DIR = os.path.dirname(os.path.abspath(__file__))

image = (
    modal.Image.from_dockerfile(
        os.path.join(OPS_DIR, "image.Dockerfile"),
        add_python="3.12",
    )
    .add_local_file(
        os.path.join(OPS_DIR, "env_loader.py"),
        "/opt/techpriest/env_loader.py",
        copy=True,
    )
    .env({"PYTHONPATH": "/opt/techpriest"})
)

projects_volume = modal.Volume.from_name("techpriest-projects", create_if_missing=True)


def _configure_git_credentials():
    helper = "!f() { printf 'username=x-access-token\\npassword=%s\\n' \"$GITHUB_TOKEN\"; }; f"
    subprocess.run(
        ["git", "config", "--global", "credential.https://github.com.helper", helper],
        check=True,
    )
    subprocess.run(
        ["git", "config", "--global", "credential.https://github.com.username", "x-access-token"],
        check=True,
    )


def _wait_for_service(timeout_seconds):
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["opencode", "service", "get", "password"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        last_error = result.stderr.strip() or result.stdout.strip()
        time.sleep(2)
    raise RuntimeError("opencode service not ready: " + last_error)


def _stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


@app.function(
    image=image,
    cpu=1,
    memory=2048,
    timeout=SESSION_SECONDS,
    scaledown_window=IDLE_SECONDS,
    volumes={"/projects": projects_volume},
    secrets=[runtime_secret],
)
def run_session(repo_url: str, worktree: str | None = None):
    if os.environ.get("GITHUB_TOKEN"):
        _configure_git_credentials()

    work = "/work/repo"
    subprocess.run(["git", "clone", repo_url, work], check=True)
    if worktree:
        linked = "/work/wt"
        subprocess.run(
            ["git", "-C", work, "worktree", "add", linked, worktree],
            check=True,
        )
        work = linked
    os.chdir(work)

    os.environ["OPENCODE_SERVER_VERSION"] = "v2"
    os.environ["OPENCODE_SERVER_MODE"] = "service"
    os.environ.setdefault("OPENCODE_MODEL_PROVIDER", "opencode")
    os.environ.setdefault("OPENCODE_MODEL_ID", "hy4-flash-free")
    os.environ.setdefault("BOT_LOCALE", "fr")

    server = subprocess.Popen(["opencode", "serve", "--service"])
    try:
        os.environ["OPENCODE_SERVER_PASSWORD"] = _wait_for_service(STARTUP_GRACE_SECONDS)
        bot = subprocess.Popen(["npx", "-y", BRIDGE_PACKAGE])
        try:
            deadline = time.monotonic() + SESSION_SECONDS - 20
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    raise RuntimeError("opencode server exited early")
                if bot.poll() is not None:
                    raise RuntimeError("telegram bridge exited early")
                time.sleep(10)
        finally:
            _stop(bot)
    finally:
        _stop(server)


if __name__ == "__main__":
    pass
