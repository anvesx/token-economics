"""Alert on a caller's spend that breaks from its own trailing baseline."""

from .anomaly import Anomaly, create

__all__ = ["Anomaly", "create"]
