"""Playwright's Node driver must inherit an existing, process-local temp directory."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from videomaker import paths


class BrowserTempTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "user's project" / 'browser_temp'

    def test_missing_profile_temp_is_replaced_and_python_cache_reset(self):
        missing = str(Path(self.temp.name) / 'missing-user' / 'Temp')
        with patch.object(paths, 'BROWSER_TEMP_DIR', self.directory), \
             patch.dict(os.environ, {'TEMP': missing, 'TMP': missing, 'TMPDIR': missing}), \
             patch.object(tempfile, 'tempdir', missing):
            result = paths.configure_browser_temp()
            self.assertTrue(result.is_dir())
            self.assertEqual({os.environ[key] for key in ('TEMP', 'TMP', 'TMPDIR')}, {str(result)})
            with tempfile.TemporaryDirectory() as created:
                self.assertEqual(Path(created).parent, result)

    def test_repeat_configuration_does_not_remove_active_browser_artifacts(self):
        with patch.object(paths, 'BROWSER_TEMP_DIR', self.directory), patch.dict(os.environ), \
             patch.object(tempfile, 'tempdir', tempfile.tempdir):
            paths.configure_browser_temp()
            artifact = self.directory / 'active.txt'
            artifact.write_text('keep', encoding='utf-8')
            paths.configure_browser_temp()
            self.assertEqual(artifact.read_text(encoding='utf-8'), 'keep')

    @unittest.skipUnless(shutil.which('node'), 'Node.js is not installed')
    def test_node_can_create_playwright_artifacts_with_apostrophe_in_parent_path(self):
        with patch.object(paths, 'BROWSER_TEMP_DIR', self.directory), patch.dict(os.environ), \
             patch.object(tempfile, 'tempdir', tempfile.tempdir):
            directory = paths.configure_browser_temp()
            code = "const fs=require('fs'),os=require('os'),path=require('path'); const p=fs.mkdtempSync(path.join(os.tmpdir(),'playwright-artifacts-')); console.log(JSON.stringify({tmp:os.tmpdir(),artifact:p})); fs.rmdirSync(p);"
            result = subprocess.run(['node', '-e', code], capture_output=True, text=True, check=True)
            value = json.loads(result.stdout)
            self.assertEqual(Path(value['tmp']).resolve(), directory)
            self.assertEqual(Path(value['artifact']).parent.resolve(), directory)


if __name__ == '__main__':
    unittest.main()
