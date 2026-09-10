#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path

import integrity_runtime as rt


class IntegrityRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "state/opportunities").mkdir(parents=True)
        (self.root / "state/decisions").mkdir(parents=True)
        self.opp = {
            "opportunity_id": "OPP-001",
            "stage": "PRE_THEME",
            "hypothesis": {"lifecycle": "ACTIVE"},
        }
        self.dec = {
            "decision_id": "DEC-001",
            "opportunity_id": "OPP-001",
            "action": "BUY",
            "result": "ALLOW",
            "trade_intent_id": "INTENT-001",
            "symbol": "600000",
            "max_quantity": 100,
            "persisted": True,
            "portfolio_refreshed": True,
            "t_plus_1_passed": True,
            "liquidity_passed": True,
            "risk_passed": True,
        }
        rt.atomic_write_json(self.root / "state/opportunities/OPP-001.json", self.opp)
        rt.atomic_write_json(self.root / "state/decisions/DEC-001.json", self.dec)

    def tearDown(self):
        self.tmp.cleanup()

    def intent(self, tid="INTENT-001"):
        return {
            "trade_intent_id": tid,
            "opportunity_id": "OPP-001",
            "decision_id": "DEC-001",
            "action": "BUY",
            "symbol": "600000",
            "quantity": 100,
            "price_policy": "LIMIT",
        }

    def test_natural_language_classification(self):
        self.assertEqual(rt.classify_mx_moni_query("查询我的持仓"), "READ_ONLY")
        self.assertEqual(rt.classify_mx_moni_query("买入 600000 100股"), "CAPITAL_MUTATION")
        self.assertEqual(rt.classify_mx_moni_query("做点事情"), "UNKNOWN")

    def test_valid_authorization(self):
        self.assertEqual(rt.authorize(self.root, self.intent())["result"], "ALLOW")

    def test_missing_decision_blocks(self):
        (self.root / "state/decisions/DEC-001.json").unlink()
        out = rt.authorize(self.root, self.intent())
        self.assertEqual(out["result"], "BLOCK")
        self.assertIn("DECISION_NOT_FOUND", out["reasons"])

    def test_wait_blocks(self):
        self.dec["result"] = "WAIT"
        rt.atomic_write_json(self.root / "state/decisions/DEC-001.json", self.dec)
        self.assertEqual(rt.authorize(self.root, self.intent())["result"], "BLOCK")

    def test_duplicate_id_blocks(self):
        self.assertEqual(rt.authorize(self.root, self.intent())["result"], "ALLOW")
        self.assertEqual(rt.authorize(self.root, self.intent())["result"], "BLOCK")

    def test_unknown_blocks_equivalent_until_reconciled(self):
        self.assertEqual(rt.authorize(self.root, self.intent())["result"], "ALLOW")
        rt.update_intent(self.root, "INTENT-001", "UNKNOWN", {"reason": "timeout"})
        # A new decision/intent for same economic request cannot bypass UNKNOWN.
        self.dec["decision_id"] = "DEC-002"
        self.dec["trade_intent_id"] = "INTENT-002"
        rt.atomic_write_json(self.root / "state/decisions/DEC-002.json", self.dec)
        new = self.intent("INTENT-002")
        new["decision_id"] = "DEC-002"
        out = rt.authorize(self.root, new)
        self.assertEqual(out["result"], "BLOCK")
        self.assertTrue(any(x.startswith("UNRESOLVED_EXECUTION") for x in out["reasons"]))

    def test_reconcile_requires_mx_moni_evidence(self):
        rt.authorize(self.root, self.intent())
        rt.update_intent(self.root, "INTENT-001", "UNKNOWN", {})
        with self.assertRaises(RuntimeError):
            rt.update_intent(self.root, "INTENT-001", "RECONCILED", {})
        out = rt.update_intent(self.root, "INTENT-001", "RECONCILED", {
            "verified_by_mx_moni": True,
            "reconciliation_evidence": "order/position query",
        })
        self.assertEqual(out["state"], "RECONCILED")

    def test_first_seen_tamper_detected(self):
        p = self.root / "state/discoveries/DISC-001.json"
        rt.atomic_write_json(p, {"discovery_id": "DISC-001", "first_seen": "2026-09-10T08:45:00+08:00"})
        self.assertEqual(rt.verify_first_seen(self.root, p)["result"], "ANCHORED")
        rt.atomic_write_json(p, {"discovery_id": "DISC-001", "first_seen": "2026-09-11T08:45:00+08:00"})
        self.assertEqual(rt.verify_first_seen(self.root, p)["reason"], "FIRST_SEEN_INTEGRITY_VIOLATION")


if __name__ == "__main__":
    unittest.main()
