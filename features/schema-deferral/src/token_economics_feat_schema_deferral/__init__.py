"""Defer tool schemas when there are many tools, keeping a server-side search path."""

from .schema_deferral import SchemaDeferral, create

__all__ = ["SchemaDeferral", "create"]
