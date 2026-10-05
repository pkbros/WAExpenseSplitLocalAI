"""Runnable check: settle math + envelope parsing + model-output coercion.
Deterministic only (no Ollama needed). Live LLM quality is verified via split.py runs.
Prints counts (e.g. 18/18 green)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from parse import coerce_expense, coerce_items, discover_senders, parse_wa_header
from settle import compute_settlement

passed = failed = 0
def ok(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS {name}")
    else:
        failed += 1
        print(f"  FAIL {name}")

print("[settle fixtures]")
s = compute_settlement([{"payer": "A", "amount": 100}, {"payer": "B", "amount": 100}])
ok("equal-no-transfer", s["transfers"] == [] and s["share_each"] == 100)
s = compute_settlement([{"payer": "A", "amount": 300}], members=["A", "B"])
ok("simple-debt", len(s["transfers"]) == 1 and s["transfers"][0] == {"from": "B", "to": "A", "amount": 150.0})
s = compute_settlement([{"payer": "A", "amount": 600}], members=["A", "B", "C"])
ok("three-way", len(s["transfers"]) == 2 and sum(t["amount"] for t in s["transfers"]) == 400)
s = compute_settlement([{"payer": "A", "amount": 0}, {"payer": "B", "amount": -5}, {"payer": "C", "amount": 90}], members=["A", "B", "C"])
ok("zero-ignored", s["grand_total"] == 90)
s = compute_settlement([{"payer": "A", "amount": 450}, {"payer": "B", "amount": 200}, {"payer": "B", "amount": 150}])
ok("conservation", abs(sum(s["net"].values())) < 0.05)

print("[envelope parsing (code owns structure)]")
h = parse_wa_header("[28/09, 21:30] Prateek Sharma: 100 sabji aata")
ok("ios-header", h["sender"] == "Prateek Sharma" and h["date"] == "2026-09-28" and h["body"] == "100 sabji aata")
h = parse_wa_header("28/09/2026, 21:30 - Atul: Sabji -->370")
ok("android-header", h["sender"] == "Atul" and h["date"] == "2026-09-28" and h["body"] == "Sabji -->370")
h = parse_wa_header("Rahul paid 200 for milk")
ok("freeform-passthrough", h["sender"] is None and h["date"] is None and h["structured"] is False)
ok("system-flagged", parse_wa_header("[28/09, 21:30] Atul: <Media omitted>")["system"] is True)
ok("join-flagged", parse_wa_header("[28/09, 21:30] Atul: joined the group")["system"] is True)
ok("senders-discovered", discover_senders(["[28/09, 21:30] Prateek Sharma: 100 sabji", "plain line"]) == ["Prateek Sharma"])
ok("bad-date-none", parse_wa_header("[99/99, 21:30] X: 100 y")["date"] is None)

print("[model-output coercion (tolerant shapes, strict money)]")
canon = ["Prateek Sharma", "Atul"]
ok("list-passthrough", coerce_items([{"a": 1}]) == [{"a": 1}])
ok("wrapper-unpacked", coerce_items({"expenses": [{"a": 1}]}) == [{"a": 1}])
ok("single-object-wrapped", coerce_items({"payer": "Atul", "amount": 40}) != [])
ok("garbage-empty", coerce_items({"foo": "bar"}) == [] and coerce_items(None) == [])
e = coerce_expense({"payer": "atul", "amount": 40, "desc": "sabji", "date": "2026-09-29"}, canon)
ok("canon-case", e is not None and e["payer"] == "Atul" and e["amount"] == 40 and e["date"] == "2026-09-29")
e = coerce_expense({"who": "Prateek Sharma", "price": 100, "item": "aata", "date": "tomorrow"}, canon)
ok("alt-keys-bad-date", e is not None and e["payer"] == "Prateek Sharma" and e["amount"] == 100 and e["date"] == "")
ok("bad-amount-rejected", coerce_expense({"payer": "A", "amount": "lots"}, canon) is None)
ok("zero-rejected", coerce_expense({"payer": "A", "amount": 0}, canon) is None)

print(f"\n{passed}/{passed+failed} green")
sys.exit(1 if failed else 0)
