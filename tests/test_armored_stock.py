from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from armored_core.armored_stock import ArmoredStock


class ArmoredStockTests(unittest.TestCase):
    def test_delegates_to_the_canonical_stock_stage_and_reports_outcomes(self):
        coordinator = type("CoordinatorStub", (), {
            "source": type("SourceStub", (), {
                "sources": (object(), object(), object()),
            })()
        })()
        expected = {
            "stage": "stock",
            "processed": 2,
            "per_source": {"source1": 1, "source2": 1, "source3": 0},
            "outcomes": {
                "downloaded": 2,
                "skipped_existing_original": 3,
                "approved_missing_original": 4,
            },
            "errors": [],
        }
        with patch(
            "armored_core.armored_stock.run_catch_up_stage",
            new=AsyncMock(return_value=expected),
        ) as run_stage:
            report = asyncio.run(ArmoredStock(coordinator).run())

        run_stage.assert_awaited_once_with(coordinator, "stock")
        self.assertEqual(report["tool"], "ArmoredStock")
        self.assertEqual(report["processed"], 2)
        self.assertEqual(report["outcomes"]["downloaded"], 2)
        self.assertEqual(report["outcomes"]["skipped_existing_original"], 3)
        self.assertEqual(report["outcomes"]["approved_missing_original"], 4)
        self.assertEqual(report["errors"], [])

    def test_refuses_a_misconfigured_source_count(self):
        coordinator = type("CoordinatorStub", (), {
            "source": type("SourceStub", (), {"sources": (object(), object())})()
        })()
        with self.assertRaisesRegex(RuntimeError, "exatamente 3 fontes"):
            asyncio.run(ArmoredStock(coordinator).run())


if __name__ == "__main__":
    unittest.main()
