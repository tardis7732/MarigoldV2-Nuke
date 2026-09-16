import marigold_nuke

import nuke

_menu = nuke.menu("Nodes").addMenu("ML/Marigold V2")
_menu.addCommand("Marigold V2", marigold_nuke.create)
_menu.addCommand("Engine/Start", marigold_nuke.start)
_menu.addCommand("Engine/Status", marigold_nuke.status)
_menu.addCommand("Engine/Stop", marigold_nuke.stop)
_menu.addCommand("Clear selected node cache", marigold_nuke.clear_cache)
