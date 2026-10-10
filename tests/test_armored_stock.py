from __future__ import annotations

import asyncio
import unittest

from ArmoredStock.service import ArmoredStock


class FakeDatabase:
    def __init__(self, *, pending_vision=None):
        self._pending_vision = pending_vision or []

    def pending_vision_candidates(self):
        return self._pending_vision

    def vision_approved_interrupted_items(self):
        return []

    def pre_download_recovery_items(self):
        return []

    def pending_vision_approved_items(self):
        return []


def coordinator_with_sources(count=3, *, pending_vision=None):
    routes = tuple(
        type("Route", (), {"source_id": f"source-{i}"})()
        for i in range(count)
    )
    source = type("Source", (), {"sources": routes})()
    return type(
        "Coordinator",
        (),
        {"source": source, "db": FakeDatabase(pending_vision=pending_vision)},
    )()


class ArmoredStockTests(unittest.TestCase):
    def test_requires_exactly_three_configured_sources(self):
        coordinator = coordinator_with_sources(2)
        with self.assertRaisesRegex(RuntimeError, "exatamente três fontes"):
            asyncio.run(ArmoredStock(coordinator).run())

    def test_blocks_downloads_while_vision_decisions_are_pending(self):
        coordinator = coordinator_with_sources(
            3, pending_vision=[object()]
        )
        with self.assertRaisesRegex(RuntimeError, "Vision ainda tem candidatos"):
            asyncio.run(ArmoredStock(coordinator).run())

    def test_returns_empty_report_when_no_approved_originals_are_pending(self):
        coordinator = coordinator_with_sources(3)
        report = asyncio.run(ArmoredStock(coordinator).run())
        self.assertEqual(report["tool"], "ArmoredStock")
        self.assertEqual(report["processed"], 0)
        self.assertEqual(report["outcomes"]["downloaded"], 0)
        self.assertEqual(report["outcomes"]["approved_missing_original"], 0)
        self.assertEqual(report["errors"], [])


if __name__ == "__main__":
    unittest.main()
