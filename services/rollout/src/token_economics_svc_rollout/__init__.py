"""Shadow runs on mirrored traffic with write isolation; later canary, kill-switch and rollback."""

from .shadow import Shadow, open_shadow

__all__ = ["Shadow", "open_shadow"]
