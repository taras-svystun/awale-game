"""Rules every agent follows, whatever its algorithm."""

import subprocess
import sys


def test_agents_never_import_pygame():
    # The engine and the agents must work without a window, e.g. in a tournament or a web version.
    code = "import sys, awale.agents; print('pygame' in sys.modules)"
    output = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout

    assert output.strip() == "False"
