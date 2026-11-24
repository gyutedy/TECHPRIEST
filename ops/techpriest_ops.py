import os
import subprocess
import time

import modal

APP_NAME = "techpriest-ops"
SESSION_SECONDS = 3600
IDLE_SECONDS = 600
STARTUP_GRACE_SECONDS = 180
BRIDGE_PACKAGE = "@grinev/opencode-telegram-bot@latest"

app = modal.App(APP_NAME)

image = modal.Image.from_dockerfile(
    path=os.path.dirname(os.path.abspath(__file__)),
    dockerfile="image.Dockerfile",
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
    memory_mib=2048,
    timeout=SESSION_SECONDS,
    idle_timeout=IDLE_SECONDS,
    volumes={"/projects": projects_volume},
    secrets=[
        modal.Secret.from_name("telegram-bot"),
        modal.Secret.from_name("github-token"),
        modal.Secret.from_name("modal-token"),
    ],
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
