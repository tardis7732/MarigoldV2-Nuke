import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_bundles = os.path.join(_root, "ofx", "build")
_current = os.environ.get("OFX_PLUGIN_PATH", "")
if _bundles not in _current.split(os.pathsep):
    os.environ["OFX_PLUGIN_PATH"] = _bundles + (os.pathsep + _current if _current else "")
