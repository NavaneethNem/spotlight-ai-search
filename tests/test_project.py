import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from project_setup import HOOK, Layout, build_files, install, uninstall

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


server = load_module("popup_server", ROOT / "app/server.py")
launcher = load_module("popup_launcher", ROOT / "app/launch.py")


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name) / "home with spaces"
        self.layout = Layout(base / "config", base / "data")
        self.layout.bindings.parent.mkdir(parents=True)
        self.original = b"-- keep this existing config\n"
        self.layout.bindings.write_bytes(self.original)

    def test_install_reinstall_uninstall(self):
        backup = install(ROOT, self.layout, activate=False)
        self.assertEqual(backup.read_bytes(), self.original)
        install(ROOT, self.layout, activate=False)
        self.assertEqual(self.layout.bindings.read_text().count(HOOK), 1)
        self.assertNotIn("@LAUNCH_COMMAND@", self.layout.module.read_text())
        self.assertIn("18476", (self.layout.app / "runtime.json").read_text())
        self.assertEqual(uninstall(self.layout, activate=False), [])
        self.assertEqual(self.layout.bindings.read_bytes(), self.original)
        self.assertFalse(self.layout.module.exists())
        self.assertFalse(self.layout.app.exists())

    def test_install_refuses_to_overwrite_user_edits(self):
        install(ROOT, self.layout, activate=False)
        self.layout.module.write_text("-- locally edited\n")
        with self.assertRaisesRegex(RuntimeError, "overwritten"):
            install(ROOT, self.layout, activate=False)
        self.assertEqual(self.layout.module.read_text(), "-- locally edited\n")

    def test_uninstall_keeps_edited_and_unrelated_files(self):
        install(ROOT, self.layout, activate=False)
        edited = self.layout.app / "app.js"
        edited.write_text("// local edits\n")
        extra = self.layout.app / "keep.txt"
        extra.write_text("keep this")
        self.assertEqual(uninstall(self.layout, activate=False), [edited])
        self.assertEqual(extra.read_text(), "keep this")
        self.assertEqual(edited.read_text(), "// local edits\n")
        self.assertEqual(self.layout.bindings.read_bytes(), self.original)

    def test_rejected_config_is_rolled_back(self):
        def result(*args):
            return subprocess.CompletedProcess(args, 0, "invalid config" if args[-1] == "configerrors" else "", "")
        with patch("project_setup.run", side_effect=result), patch("project_setup.subprocess.run"):
            with self.assertRaisesRegex(RuntimeError, "rejected"):
                install(ROOT, self.layout, activate=True)
        self.assertEqual(self.layout.bindings.read_bytes(), self.original)
        self.assertFalse(self.layout.module.exists())
        self.assertFalse(self.layout.app.exists())

    def test_port_and_unowned_destination_validation(self):
        with self.assertRaises(ValueError):
            build_files(ROOT, self.layout, 80)
        self.layout.app.mkdir(parents=True)
        (self.layout.app / "keep.txt").write_text("keep")
        with self.assertRaisesRegex(RuntimeError, "ownership receipt"):
            install(ROOT, self.layout, activate=False)
        self.assertEqual((self.layout.app / "keep.txt").read_text(), "keep")


class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = server.create_server(0)
        cls.base = "http://127.0.0.1:" + str(cls.http.server_port)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join(timeout=2)

    def test_form_routing_and_content_headers(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output), urllib.request.urlopen(self.base + "/spotlight-ai") as response:
            page = response.read().decode()
            self.assertIn('name="udm" value="50"', page)
            self.assertIn('name="aep" value="11"', page)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertNotIn("Access-Control-Allow-Origin", response.headers)
        self.assertEqual(output.getvalue(), "")

    def test_only_allowlisted_assets_are_served(self):
        for path in ("/../project_setup.py", "/runtime.json"):
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(self.base + path)
            self.assertEqual(error.exception.code, 404)
            error.exception.close()

    def test_unexpected_host_is_rejected(self):
        request = urllib.request.Request(self.base + "/spotlight-ai", headers={"Host": "example.invalid"})
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request)
        self.assertEqual(error.exception.code, 403)
        error.exception.close()

    def test_remote_failure_does_not_break_manual_search(self):
        with patch.object(server, "suggestions", side_effect=OSError("offline")):
            with urllib.request.urlopen(self.base + "/api/suggest?q=example") as response:
                self.assertEqual(json.load(response), [])

    def test_autocomplete_cache_and_five_row_limit(self):
        server.CACHE.clear()
        payload = json.dumps(["example", ["example " + str(i) for i in range(8)]]).encode()
        with patch.object(server.urllib.request, "urlopen", return_value=io.BytesIO(payload)) as remote:
            self.assertEqual(len(server.suggestions("Example")), 5)
            self.assertEqual(len(server.suggestions("example")), 5)
            self.assertEqual(remote.call_count, 1)


class LauncherTests(unittest.TestCase):
    def test_fresh_closes_only_its_own_popup(self):
        other = {"address": "0xother", "class": "brave-browser"}
        popup = {"address": "0xpopup", "class": launcher.CLASS}
        with patch.object(launcher, "clients", side_effect=[[other, popup], [other]]), patch.object(launcher.subprocess, "run") as dispatch:
            launcher.fresh()
            self.assertEqual(dispatch.call_count, 1)
            self.assertIn("address:0xpopup", dispatch.call_args.args[0][2])
            self.assertNotIn("address:0xother", dispatch.call_args.args[0][2])


if __name__ == "__main__":
    unittest.main()
