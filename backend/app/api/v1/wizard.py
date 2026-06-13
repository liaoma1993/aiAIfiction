"""Wizard API router facade.

The wizard workflow is large enough to live outside the API package. Keep this
module as the stable import path used by `app.api.v1.router`.
"""

from app.services.wizard.routes import router

__all__ = ["router"]
