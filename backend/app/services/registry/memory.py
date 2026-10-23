"""
Compatibility shim.

The in-memory registry was replaced by PostgreSQL-backed DocumentRegistry
in Task A. Import from app.services.registry.store instead.
"""

from app.services.registry.store import DocumentRegistry, PersistenceError

__all__ = ["DocumentRegistry", "PersistenceError"]
