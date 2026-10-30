import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "release_built", Path(__file__).with_name("release-built.py")
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseBuildTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.output = Path(self.work.name) / "outputs"
        self.env = patch.dict(os.environ, {
            "GITHUB_REPOSITORY": "owner/browser", "RUN_ID": "123",
            "GITHUB_OUTPUT": str(self.output),
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.run = {
            "status": "completed", "conclusion": "success",
            "event": "workflow_dispatch", "head_branch": "main",
            "path": ".github/workflows/build.yml",
            "head_repository": {"full_name": "owner/browser"},
            "head_sha": "a" * 40,
        }

    def test_publishes_exact_successful_build_commit(self):
        with patch.object(release, "api", return_value=self.run) as api:
            release.main()
        api.assert_called_once_with("repos/owner/browser/actions/runs/123")
        self.assertEqual(self.output.read_text(), f"sha={'a' * 40}\ntag=build-123\n")

    def test_rejects_unfinished_failed_or_unrelated_runs(self):
        for field, value in [
            ("status", "in_progress"), ("conclusion", "failure"),
            ("event", "pull_request"), ("head_branch", "other"),
            ("path", ".github/workflows/check.yml"),
            ("head_repository", {"full_name": "fork/browser"}),
            ("head_sha", "main"),
        ]:
            with self.subTest(field=field), patch.object(
                release, "api", return_value={**self.run, field: value}
            ), self.assertRaises(SystemExit):
                release.main()
            self.assertFalse(self.output.exists())

    def test_rejects_non_numeric_id_before_api_access(self):
        with patch.dict(os.environ, RUN_ID="../other"), patch.object(
            release, "api"
        ) as api, self.assertRaises(SystemExit):
            release.main()
        api.assert_not_called()


if __name__ == "__main__":
    unittest.main()
