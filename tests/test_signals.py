import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from observer.signals import evaluate

TH = {"funding_abs": 0.0005, "mom_15m_abs_pct": 2.0, "mom_1h_abs_pct": 3.5,
      "book_imbalance_abs": 0.45, "book_min_depth_usd": 100000,
      "ls_ratio_high": 1.6, "ls_ratio_low": 0.6, "oi_change_1h_abs_pct": 5.0}

BASE = {"symbol": "TESTUSDT", "funding_rate": 0.0001, "mom_15m_pct": 0.5, "mom_1h_pct": 1.0,
        "bid_depth_1pct_usd": 500000, "ask_depth_1pct_usd": 480000, "imbalance_1pct": 0.02,
        "ls_ratio": 1.1, "open_interest": 1000.0}


class SignalsTest(unittest.TestCase):
    def test_quiet_market_no_alerts(self):
        self.assertEqual(evaluate(dict(BASE), None, TH), [])

    def test_extreme_funding_alerts(self):
        s = dict(BASE, funding_rate=0.0012)
        alerts = evaluate(s, None, TH)
        self.assertTrue(any("资金费率" in a for a in alerts))

    def test_thin_book_imbalance_ignored(self):
        s = dict(BASE, imbalance_1pct=0.9, bid_depth_1pct_usd=1000, ask_depth_1pct_usd=100)
        self.assertFalse(any("盘口" in a for a in evaluate(s, None, TH)))

    def test_oi_change_alerts(self):
        prev = dict(BASE, open_interest=900.0)
        alerts = evaluate(dict(BASE), prev, TH)
        self.assertTrue(any("持仓量" in a for a in alerts))


class WhaleFilterTest(unittest.TestCase):
    def test_threshold_filters(self):
        # 模拟 Blockchair 行：output_total 为 satoshi 单位，None 要容错
        rows = [
            {"hash": "a", "time": "t", "output_total": 150_00000000, "output_total_usd": 100000},
            {"hash": "b", "time": "t", "output_total": 50_00000000, "output_total_usd": 50000},
            {"hash": "c", "time": "t", "output_total": None, "output_total_usd": None},
        ]
        import observer.whale as whale
        orig = whale._get_json
        whale._get_json = lambda url: {"data": rows}
        try:
            out, status = whale.blockchair_large("bitcoin", 100.0)
        finally:
            whale._get_json = orig
        self.assertEqual(status, "ok")
        self.assertEqual([t["hash"] for t in out], ["a"])
        self.assertEqual(out[0]["value_native"], 150.0)


if __name__ == "__main__":
    unittest.main()
