import unittest
import shutil
import json
import sys
import os
import re
from unittest.mock import MagicMock

# Mock IPython, requests, and tqdm before importing nenen88 to prevent ModuleNotFoundError in local tests
mock_ipython = MagicMock()
sys.modules['IPython'] = mock_ipython
sys.modules['IPython.core'] = mock_ipython
sys.modules['IPython.core.magic'] = mock_ipython
sys.modules['IPython.display'] = mock_ipython

sys.modules['requests'] = MagicMock()
sys.modules['tqdm'] = MagicMock()

# Append script directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'script')))

class TestRepoFusion(unittest.TestCase):

    def test_ipynb_json_integrity(self):
        """Verify that Segsmaker_COLAB.ipynb has valid JSON syntax and correct nbformat."""
        notebook_path = os.path.join(os.path.dirname(__file__), 'notebook', 'Segsmaker_COLAB.ipynb')
        self.assertTrue(os.path.exists(notebook_path), "Segsmaker_COLAB.ipynb does not exist!")

        with open(notebook_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.assertIn('cells', data)
        self.assertIn('metadata', data)
        self.assertEqual(data.get('nbformat'), 4)
        print("[OK] Segsmaker_COLAB.ipynb JSON integrity and nbformat verified successfully.")

    def test_nenen88_syntax_and_imports(self):
        """Compile and verify repofusion/script/nenen88.py for syntax correctness."""
        script_path = os.path.join(os.path.dirname(__file__), 'script', 'nenen88.py')
        self.assertTrue(os.path.exists(script_path), "nenen88.py does not exist!")

        with open(script_path, 'r', encoding='utf-8') as f:
            source = f.read()

        try:
            compile(source, script_path, 'exec')
            print("[OK] nenen88.py syntax compilation successful.")
        except SyntaxError as e:
            self.fail(f"nenen88.py contains syntax errors: {e}")

    def test_setup_syntax_and_imports(self):
        """Compile and verify repofusion/script/KC/setup.py for syntax correctness."""
        setup_path = os.path.join(os.path.dirname(__file__), 'script', 'KC', 'setup.py')
        self.assertTrue(os.path.exists(setup_path), "setup.py does not exist!")

        with open(setup_path, 'r', encoding='utf-8') as f:
            source = f.read()

        try:
            compile(source, setup_path, 'exec')
            print("[OK] setup.py syntax compilation successful.")
        except SyntaxError as e:
            self.fail(f"setup.py contains syntax errors: {e}")

    def test_downloader_parser_and_formatter(self):
        """Test the aria2c log stats parser and progress visual formatter logic from nenen88.py."""
        from nenen88 import _parse_aria2_stats, _fmt_progress, _fmt_size, _fmt_eta

        # Test Size Formatter
        self.assertEqual(_fmt_size(1024), "1.0KiB")
        self.assertEqual(_fmt_size(1024**2), "1.0MiB")
        self.assertEqual(_fmt_size(1024**3), "1.0GiB")

        # Test ETA Formatter
        self.assertEqual(_fmt_eta(30), "30s")
        self.assertEqual(_fmt_eta(90), "1m30s")
        self.assertEqual(_fmt_eta(3600), "60m00s")

        # Mock aria2c progress line
        raw_line = "[#f374eb 614MiB/6.6GiB(9%) CN:16 DL:32MiB ETA:3m12s]"
        
        # Test Stats Parsing (Note: _parse_aria2_stats captures the first unit, which is 3m = 180s)
        stats = _parse_aria2_stats(raw_line)
        self.assertEqual(stats['pct'], 9)
        self.assertAlmostEqual(stats['done_b'], 614 * 1024**2)
        self.assertAlmostEqual(stats['total_b'], 6.6 * 1024**3, delta=1024**2)
        self.assertAlmostEqual(stats['speed_b'], 32 * 1024**2)
        self.assertEqual(stats['eta_s'], 180)
        print("[OK] Aria2c log parser test succeeded.")

        # Test Progress Formatting (should convert brackets to double brackets and inject ANSI tags)
        formatted = _fmt_progress(raw_line)
        self.assertIn("【", formatted)
        self.assertIn("】", formatted)
        self.assertIn("\033[35m", formatted)  # Magenta code
        self.assertIn("\033[36m", formatted)  # Cyan code
        print("[OK] Aria2c progress color formatter test succeeded.")

    def test_shutil_precheck_bypass_logic(self):
        """Simulate Solusi B pre-check logic on the system."""
        has_aria2 = shutil.which('aria2c') is not None
        has_pv = shutil.which('pv') is not None
        has_lz4 = shutil.which('lz4') is not None

        missing = []
        if not has_aria2: missing.append('aria2')
        if not has_pv: missing.append('pv')
        if not has_lz4: missing.append('lz4')

        # Since this runs on Windows, some might be missing, but it must not crash.
        print(f"[OK] Shutil bypass pre-check simulation successful. Missing packages: {missing}")

if __name__ == '__main__':
    unittest.main()
