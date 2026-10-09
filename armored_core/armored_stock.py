from __future__ import annotations

from typing import Any

from .catch_up_stages import run_catch_up_stage


class ArmoredStock:
    """Independent CLI facade for the durable, Vision-approved download stage.

    The stage implementation remains centralized in catch_up_stages.py so the
    standalone tool and the staged catch-up command cannot drift apart. Stock
    materializes approved ORIGINAL files only; it does not run IA, Studio/RVC,
    Hub, publication, cleanup, or LIVE cutover.
    """

    def __init__(self, coordinator: Any) -> None:
        self.coordinator = coordinator

    async def run(self) -> dict[str, Any]:
        source = self.coordinator.source
        routes = tuple(getattr(source, "sources", ()))
        if len(routes) != 3:
            raise RuntimeError(
                "ArmoredStock exige exatamente 3 fontes configuradas em project.env; "
                f"encontradas {len(routes)}."
            )

        report = await run_catch_up_stage(self.coordinator, "stock")
        outcomes = report.get("outcomes", {})
        return {
            "tool": "ArmoredStock",
            "processed": int(report.get("processed", 0)),
            "per_source": report.get("per_source", {}),
            "outcomes": {
                "downloaded": int(outcomes.get("downloaded", report.get("processed", 0))),
                "skipped_existing_original": int(outcomes.get("skipped_existing_original", 0)),
                "approved_missing_original": int(outcomes.get("approved_missing_original", 0)),
            },
            "errors": list(report.get("errors", [])),
        }
