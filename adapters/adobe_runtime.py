"""Unified Adobe tool runtime adapter."""

from __future__ import annotations

from typing import Any, Literal

from adapters.after_effects_runtime import AfterEffectsAutomationAdapter
from adapters.photoshop_runtime import PhotoshopAutomationAdapter

AdobeTool = Literal["photoshop", "after_effects"]


class AdobeAutomationAdapter:
    """Coordinates Photoshop and After Effects runtime adapters."""

    def __init__(self) -> None:
        self.photoshop = PhotoshopAutomationAdapter()
        self.after_effects = AfterEffectsAutomationAdapter()

    def get_status(self, tool: AdobeTool | None = None) -> dict[str, Any]:
        ps_status = self.photoshop.get_status()
        ae_status = self.after_effects.get_status()

        if tool == "photoshop":
            return ps_status
        if tool == "after_effects":
            return ae_status
        return {"photoshop": ps_status, "after_effects": ae_status}

    def load_runtime(self, tool: AdobeTool) -> dict[str, Any]:
        if tool == "photoshop":
            return self.photoshop.load_runtime()
        if tool == "after_effects":
            return self.after_effects.load_runtime()
        raise ValueError(f"Unknown Adobe tool: {tool}")
