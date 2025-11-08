"""Import wrapper for global hook: global_test_hook"""

import sys
from pathlib import Path

# Add global hooks to path
global_hooks_path = Path.home() / ".quickhooks"
if str(global_hooks_path) not in sys.path:
    sys.path.insert(0, str(global_hooks_path))

# Import the global hook
from hooks.global_test_hook import *
