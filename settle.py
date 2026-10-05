"""S3 settle core: deterministic money math. No LLM, no guessing.
Usage: python settle.py data/03_expenses.json --out data/04_settlement.json
"""
import argparse
import json
from pathlib import Path


def compute_settlement(expenses, members=None):
    """expenses: [{payer, amount, ...}]. Equal split. Returns dict with totals + min transfers."""
    totals = {}
    grand = 0.0
    for e in expenses:
        try:
            amt = float(e.get("amount", 0))
        except (ValueError, TypeError):
            continue
        if amt <= 0:
            continue
        payer = str(e.get("payer", "Unknown")).strip() or "Unknown"
        totals[payer] = totals.get(payer, 0.0) + amt
        grand += amt
    if members:
        for m in members:
            totals.setdefault(m, 0.0)
    n = len(totals) or 1
    share = round(grand / n, 2) if n else 0.0
    nets = {p: round(paid - share, 2) for p, paid in totals.items()}
    # Greedy min-cash-flow: debtors pay creditors
    debtors = sorted([(p, -v) for p, v in nets.items() if v < -0.005], key=lambda x: -x[1])
    creditors = sorted([(p, v) for p, v in nets.items() if v > 0.005], key=lambda x: -x[1])
    transfers = []
    i = j = 0
    debtors = [[p, a] for p, a in debtors]
    creditors = [[p, a] for p, a in creditors]
    while i < len(debtors) and j < len(creditors):
        dp, da = debtors[i]
        cp, ca = creditors[j]
        x = round(min(da, ca), 2)
        if x > 0.005:
            transfers.append({"from": dp, "to": cp, "amount": x})
        debtors[i][1] = round(da - x, 2)
        creditors[j][1] = round(ca - x, 2)
        if debtors[i][1] <= 0.005:
            i += 1
        if creditors[j][1] <= 0.005:
            j += 1
    return {
        "grand_total": round(grand, 2),
        "members": sorted(totals),
        "paid": {k: round(v, 2) for k, v in totals.items()},
        "share_each": share,
        "net": nets,
        "transfers": transfers,
        "count": len(expenses),
    }


def summary_text(s):
    lines = [f"Total Rs.{s['grand_total']:.0f} / {len(s['members'])} = Rs.{s['share_each']:.0f} each"]
    for m in s["members"]:
        lines.append(f"- {m} paid Rs.{s['paid'][m]:.0f} (net {s['net'][m]:+.0f})")
    if not s["transfers"]:
        lines.append("All settled. No transfers needed.")
    else:
        lines.append("Settle:")
        for t in s["transfers"]:
            lines.append(f"- {t['from']} pays {t['to']} Rs.{t['amount']:.0f}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="03_expenses.json (or 02_parsed.json with .expenses key)")
    ap.add_argument("--out", default="data/04_settlement.json")
    ap.add_argument("--members", default="", help="comma list to include zero-paid members")
    args = ap.parse_args()
    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    expenses = raw.get("expenses", raw) if isinstance(raw, dict) else raw
    members = [m.strip() for m in args.members.split(",") if m.strip()] or None
    s = compute_settlement(expenses, members)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")
    print(summary_text(s))
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
