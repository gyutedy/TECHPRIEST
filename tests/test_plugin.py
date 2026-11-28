import hashlib
import importlib.util
import json
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".opencode" / "opencode.jsonc"
TECHPRIEST = ROOT / ".opencode" / "agents" / "techpriest.md"
SERVITOR = ROOT / ".opencode" / "agents" / "servitor.md"
OPS = ROOT / "ops" / "techpriest_ops.py"
DOCKERFILE = ROOT / "ops" / "image.Dockerfile"
TEMPLATE = ROOT / "MODELE_RITES.md"
INSTALL_PS = ROOT / "ops" / "install.ps1"
INSTALL_SH = ROOT / "ops" / "install.sh"


def text(path):
    return path.read_text(encoding="utf-8")


def frontmatter(path):
    parts = text(path).split("---", 2)
    return parts[1] if len(parts) > 2 else ""


def has_rule(frontmatter_text, action, resource, effect):
    pattern = (
        r"action:\s*"
        + re.escape(action)
        + r"\s*\n\s*resource:\s*\"?"
        + re.escape(resource)
        + r"\"?\s*\n\s*effect:\s*"
        + re.escape(effect)
    )
    return re.search(pattern, frontmatter_text) is not None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Structure(unittest.TestCase):
    def test_required_files(self):
        required = (
            CONFIG,
            TECHPRIEST,
            SERVITOR,
            OPS,
            DOCKERFILE,
            INSTALL_PS,
            INSTALL_SH,
            TEMPLATE,
            ROOT / "README.md",
            ROOT / "LICENSE",
        )
        for path in required:
            self.assertTrue(path.is_file(), "missing " + str(path))

    def test_config_is_valid_and_safe(self):
        config = json.loads(text(CONFIG))
        self.assertEqual(config["$schema"], "https://opencode.ai/config.json")
        self.assertEqual(config["model"], "opencode/hy4-flash-free")
        self.assertEqual(config["default_agent"], "techpriest")
        self.assertIn("RITES.md", config["instructions"])
        self.assertIn(
            {"action": "shell", "resource": "rm -rf *", "effect": "deny"},
            config["permissions"],
        )

    def test_rites_template_fields(self):
        content = text(TEMPLATE)
        for field in ("Projet :", "Installer :", "Lancer :", "Tester :", "Déboguer :", "Jobs distants :", "Interdits :"):
            self.assertIn(field, content)


class Agents(unittest.TestCase):
    def test_techpriest_frontmatter(self):
        meta = frontmatter(TECHPRIEST)
        self.assertIn("mode: primary", meta)
        self.assertIn("model: opencode/hy4-flash-free", meta)
        for resource in ("git push *", "gh workflow run *", "modal run *"):
            self.assertTrue(has_rule(meta, "shell", resource, "ask"), resource)
        self.assertTrue(has_rule(meta, "shell", "rm -rf *", "deny"))
        for resource in ("TECHPRIEST/**", ".opencode/**", "ops/**"):
            self.assertTrue(has_rule(meta, "edit", resource, "deny"), resource)
        self.assertTrue(has_rule(meta, "subagent", "servitor", "allow"))

    def test_techpriest_refuses_without_rites(self):
        body = text(TECHPRIEST).split("---", 2)[2]
        self.assertIn("RITES.md", body)
        self.assertIn("REFUSE", body)
        self.assertIn("jamais l'inventer", body)

    def test_servitor_is_read_only(self):
        meta = frontmatter(SERVITOR)
        self.assertIn("mode: subagent", meta)
        self.assertTrue(has_rule(meta, "edit", "*", "deny"))
        self.assertTrue(has_rule(meta, "shell", "*", "deny"))

    def test_model_is_a_single_switch(self):
        brain = text(CONFIG) + text(TECHPRIEST)
        self.assertEqual(brain.count("opencode/hy4-flash-free"), 2)
        self.assertNotIn("deepseek-v4.1-flash-free", brain)


class RemoteOps(unittest.TestCase):
    def test_session_bounds_and_secrets(self):
        content = text(OPS)
        self.assertIn("SESSION_SECONDS = 3600", content)
        self.assertIn("IDLE_SECONDS = 600", content)
        self.assertIn("timeout=SESSION_SECONDS", content)
        self.assertIn("scaledown_window=IDLE_SECONDS", content)
        self.assertIn("modal.Secret.from_dict", content)
        self.assertIn("load_env_file()", content)
        self.assertNotIn("modal.Secret.from_name", content)
        self.assertIn("OPENCODE_SERVER_VERSION", content)
        self.assertIn("v2", content)
        self.assertIn("npx", content)

    def test_image_contains_toolchain(self):
        content = text(DOCKERFILE)
        for needle in ("ubuntu:24.04", "opencode.ai/install", "setup_22.x", " gh ", "modal", "WORKDIR /work"):
            self.assertIn(needle, content)

    def test_installers(self):
        self.assertIn("RITES.md", text(INSTALL_PS))
        self.assertIn(".opencode", text(INSTALL_PS))
        self.assertIn("RITES.md", text(INSTALL_SH))
        self.assertIn(".opencode", text(INSTALL_SH))


class LocalEnv(unittest.TestCase):
    def _loader(self):
        path = ROOT / "ops" / "env_loader.py"
        spec = importlib.util.spec_from_file_location("env_loader", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_template_and_gitignore(self):
        template = text(ROOT / "env_techpriest.example")
        for key in (
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_ALLOWED_USER_ID",
            "GITHUB_TOKEN",
            "MODAL_TOKEN_ID",
            "MODAL_TOKEN_SECRET",
        ):
            self.assertIn(key + "=", template)
            self.assertTrue(template.split(key + "=")[1].splitlines()[0] == "")
        self.assertIn("env_techpriest", text(ROOT / ".gitignore"))

    def test_loader_rules(self):
        loader = self._loader()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "env_techpriest").write_text(
                "# commentaire\n\nA_TEST_KEY=depuis_fichier\nB_TEST_KEY=\n",
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"A_TEST_KEY": "deja_posee"}, clear=False):
                self.assertEqual(loader.load_env_file(str(root)), [])
                self.assertEqual(os.environ["A_TEST_KEY"], "deja_posee")
            with mock.patch.dict(os.environ, {}, clear=True):
                self.assertEqual(loader.load_env_file(str(root)), ["A_TEST_KEY"])
                self.assertEqual(os.environ["A_TEST_KEY"], "depuis_fichier")
            (root / ".env").write_text("A_TEST_KEY=dotenv\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {}, clear=True):
                loader.load_env_file(str(root))
                self.assertEqual(os.environ["A_TEST_KEY"], "dotenv")

    def test_missing_keys(self):
        loader = self._loader()
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(loader.missing_keys(("A_TEST_KEY",)), ["A_TEST_KEY"])
            self.assertEqual(loader.local_secret_values(("A_TEST_KEY",)), {})


class Doctrine(unittest.TestCase):
    def test_no_literal_secret_values(self):
        github = "gh" + "p" + "ousr" + "_[A-Za-z0-9]{20,}"
        telegram = r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"
        modal = "MODAL_TOKEN_" + "SECRET" + r"\s*=\s*[\"'][^\"']+[\"']"
        patterns = [re.compile(p) for p in (github, telegram, modal)]
        offenders = []
        for path in ROOT.rglob("*"):
            if path.suffix not in (".py", ".jsonc") or "tests" in path.parts:
                continue
            for number, line in enumerate(text(path).splitlines(), 1):
                for pattern in patterns:
                    if pattern.search(line):
                        offenders.append(str(path.relative_to(ROOT)) + ":" + str(number))
        self.assertEqual(offenders, [], "literal secrets: " + ", ".join(offenders))


class Portability(unittest.TestCase):
    def test_copy_into_unrelated_host_changes_nothing(self):
        plugin_files = [
            path
            for path in ROOT.rglob("*")
            if path.is_file()
            and ".git" not in path.parts
            and "__pycache__" not in path.parts
        ]
        before = {path.relative_to(ROOT): digest(path) for path in plugin_files}
        with tempfile.TemporaryDirectory() as tmp:
            host = Path(tmp) / "host"
            host.mkdir()
            (host / "host_app.py").write_text("HOST = True\n", encoding="utf-8")
            (host / "RITES.md").write_text("Projet : autre\n", encoding="utf-8")
            for path in plugin_files:
                relative = path.relative_to(ROOT)
                destination = host / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, destination)
            self.assertTrue((host / ".opencode" / "opencode.jsonc").is_file())
            self.assertEqual((host / "host_app.py").read_text(encoding="utf-8"), "HOST = True\n")
        after = {path.relative_to(ROOT): digest(path) for path in plugin_files}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
