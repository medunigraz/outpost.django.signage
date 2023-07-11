from . import api

v1 = [
    (r"signage/playlist", api.PlaylistViewSet, "signage-playlist"),
]
