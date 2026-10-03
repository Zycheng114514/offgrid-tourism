"""End-to-end tests with the simulated model: no network, no real model."""

import json
import unittest

from offgrid.dialog import Dialog
from offgrid.gateway import parse_smsgate_webhook, verify_signature
from offgrid.llm import LLM, LLMConfig
from offgrid.pack import build_pack
from offgrid.region import ROOT, Region
from offgrid.rules import parse_hours, parse_price
from offgrid.search import find
from offgrid.seed import load_seed
from offgrid.store import Store

REGION = Region("regions/samosir.json")
EXAMPLES = json.loads((ROOT / "models/simulated/samosir.json").read_text())


def make(provider="simulated"):
    store = Store(":memory:")
    llm = LLM(LLMConfig(provider=provider, simulated_path=str(ROOT / "models/simulated/samosir.json")))
    sent = []
    return Dialog(REGION, store, llm, lambda phone, text: sent.append((phone, text))), store, sent


class Rules(unittest.TestCase):
    def test_prices(self):
        cases = {"nasi ikan 25rb": 25000, "Rp 25.000": 25000, "kamar 1,5jt per malam": 1500000, "100-150rb per org": 100000}
        for text, lo in cases.items():
            self.assertEqual(parse_price(text, REGION)[0]["min"], lo, text)
        self.assertIsNone(parse_price("3 kamar", REGION)[0])
        self.assertEqual(parse_price("150rb/mlm", REGION)[0]["unit"], "per_night")
        self.assertEqual(parse_price("200rb sehari", REGION)[0]["unit"], "per_day")
        self.assertEqual(parse_price("25rb", REGION)[0]["unit"], "other")

    def test_hours(self):
        self.assertEqual(parse_hours("buka 7-21", REGION), {"open": "07:00", "close": "21:00"})
        self.assertEqual(parse_hours("jam 8 pagi sampai 8 malam", REGION), {"open": "08:00", "close": "20:00"})
        self.assertIsNone(parse_hours("3-4 orang", REGION))


class HostExamples(unittest.TestCase):
    def test_every_example_ends_confirmed(self):
        for ex in EXAMPLES["host_examples"]:
            if not ex["llm_output"]:
                continue
            dialog, store, sent = make()
            phone = "+6200000099" + ex["id"][-1]
            dialog.handle(phone, ex["message"])
            for answer in ex["answers"]:
                dialog.handle(phone, answer)
            listings = store.listings(REGION.id)
            self.assertEqual(len(listings), 1, ex["id"])
            l = listings[0]
            self.assertEqual(l["status"]["state"], "confirmed", (ex["id"], sent))
            self.assertIsNone(store.conversation(phone), ex["id"])

    def test_invented_name_is_rejected(self):
        dialog, store, sent = make()
        dialog.handle("+620000009999", "ada kamar kosong di ambarita malam ini, 200rb")
        l = store.listings(REGION.id)[0]
        self.assertIsNone(l["name"])
        self.assertIn("name", l["extraction"]["rejected_model_values"])
        self.assertEqual(sent[-1][1], REGION.template("ask_name"))

    def test_unknown_message_falls_back_to_rules(self):
        dialog, store, sent = make()
        dialog.handle("+620000009998", "INAP kamar di Tuk Tuk 300rb/mlm")
        l = store.listings(REGION.id)[0]
        self.assertEqual((l["village"], l["price"]["min"], l["price"]["unit"]), ("Tuk Tuk", 300000, "per_night"))
        self.assertEqual(l["extraction"]["llm_error"], "no simulated output for this message")

    def test_closed_today(self):
        dialog, store, sent = make()
        phone = "+620000009997"
        for t in ["MAKAN Warung Bu Sinaga di Garoga, nasi ikan 25rb, buka 7-21", "1", "YA", "TUTUP"]:
            dialog.handle(phone, t)
        self.assertIs(store.listings(REGION.id)[0]["status"]["open_today"], False)
        self.assertEqual(sent[-1][1], REGION.template("closed_ack"))


class Traveller(unittest.TestCase):
    def setUp(self):
        self.dialog, self.store, self.sent = make()
        load_seed(ROOT / "data/synthetic/seed_listings_samosir.json", REGION, self.store)

    def test_sms_search(self):
        reply = self.dialog.handle("+15550000000", "SEARCH food Garoga")
        self.assertTrue(reply.startswith("Results:"))
        self.assertIn("Lapo Tepi Danau", reply)

    def test_pack_hides_phone_without_consent(self):
        pack = build_pack(REGION, self.store)
        hidden = [l for l in pack["listings"] if l["name"] == "Warung Mak Tio"][0]
        self.assertIsNone(hidden["phone"])
        self.assertTrue(all(l["data_origin"] == "synthetic" for l in pack["listings"]))

    def test_find_ranks_matching_words(self):
        self.assertEqual(find("boat", REGION, self.store.listings(REGION.id))[0]["name"], "Kapal Bapak Sitanggang")


class Trace(unittest.TestCase):
    def test_trace_is_a_dry_run_with_all_steps(self):
        from offgrid.trace import trace
        store = Store(":memory:")
        llm = LLM(LLMConfig(provider="simulated", simulated_path=str(ROOT / "models/simulated/samosir.json")))
        out = trace("MAKAN Warung Bu Sinaga di Garoga, nasi ikan 25rb, buka 7-21", REGION, llm, store)
        ids = [s["id"] for s in out["steps"]]
        self.assertEqual(ids, ["sms", "gateway", "route", "rules", "model", "checks", "merge", "ask", "store", "pack", "traveller"])
        self.assertEqual(store.listings(), [])
        self.assertEqual(out["steps"][-1]["data"]["rank"], 1)

    def test_trace_shows_rejected_name(self):
        from offgrid.trace import trace
        llm = LLM(LLMConfig(provider="simulated", simulated_path=str(ROOT / "models/simulated/samosir.json")))
        out = trace("ada kamar kosong di ambarita malam ini, 200rb", REGION, llm, Store(":memory:"))
        checks = {c["field"]: c for c in out["steps"][5]["data"]["checks"]}
        self.assertEqual(checks["name"]["result"], "rejected")


class Gateway(unittest.TestCase):
    def test_webhook_payload(self):
        body = {"event": "sms:received", "id": "x1", "payload": {"messageId": "m1", "message": "BUKA", "sender": "+15551234567"}}
        self.assertEqual(parse_smsgate_webhook(body), ("m1", "+15551234567", "BUKA"))
        self.assertIsNone(parse_smsgate_webhook({"event": "sms:sent"}))

    def test_signature(self):
        import hashlib, hmac
        sig = hmac.new(b"k", b'{"a":1}' + b"123", hashlib.sha256).hexdigest()
        self.assertTrue(verify_signature("k", b'{"a":1}', "123", sig))
        self.assertFalse(verify_signature("k", b'{"a":2}', "123", sig))


if __name__ == "__main__":
    unittest.main()


class Languages(unittest.TestCase):
    def setUp(self):
        self.dialog, self.store, self.sent = make()
        load_seed(ROOT / "data/synthetic/seed_listings_samosir.json", REGION, self.store)

    def test_batak_report_gets_indonesian_questions(self):
        reply = self.dialog.handle("+620000007001", "adong kamar modom di Ambarita, 2 kamar, 150rb sada borngin, boi mangan manogot")
        self.assertEqual(reply, REGION.template("ask_name", "id"))
        self.assertEqual(self.store.host_for("+620000007001")["lang"], "bbc")

    def test_english_report_gets_english_replies(self):
        phone = "+620000007002"
        first = self.dialog.handle(phone, "Homestay Sunset View in Tuk Tuk, 3 rooms with lake view, 250rb per night incl breakfast")
        self.assertTrue(first.startswith("We noted:"), first)
        self.assertEqual(self.dialog.handle(phone, "1"), REGION.template("ask_publish_phone", "en"))

    def test_chinese_search(self):
        reply = self.dialog.handle("+8613800000000", "搜索 便宜 住宿 Tomok")
        self.assertTrue(reply.startswith("结果："), reply)
        self.assertIn("/晚", reply)

    def test_question_without_keyword_is_a_search(self):
        self.assertTrue(self.dialog.handle("+15550000001", "where can I eat in Garoga?").startswith("Results:"))

    def test_chit_chat_creates_nothing(self):
        before = len(self.store.listings())
        reply = self.dialog.handle("+15550000002", "what are you doing")
        self.assertEqual(reply, REGION.template("help", "en"))
        self.assertEqual(len(self.store.listings()), before)

    def test_unknown_language_gets_both_default_languages(self):
        reply = self.dialog.handle("+15550000003", "zzz qqq")
        self.assertIn(REGION.template("not_understood", "id"), reply)
        self.assertIn(REGION.template("not_understood", "en"), reply)
