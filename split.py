"""S4 orchestrator: chains parse -> curate -> settle via disk artifacts only.
Usage: python split.py data/01_raw.txt --out data
Artifacts: 02_parsed.json -> 03_expenses.json -> 04_settlement.json (additive, immutable)
Requires Ollama running locally. No fallback: parse failure exits non-zero with setup help.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import load_config
from settle import compute_settlement, summary_text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="raw chat .txt")
    ap.add_argument("--out", default="data")
    args = ap.parse_args()
    cfg = load_config()
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    raw_text = Path(args.input).read_text(encoding="utf-8")
    (outdir / "01_raw.txt").write_text(raw_text, encoding="utf-8")

    cmd = [sys.executable, str(Path(__file__).parent / "parse.py"),
           str(outdir / "01_raw.txt"), "--out", str(outdir / "02_parsed.json")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout.strip())
    if r.stderr.strip():
        print(r.stderr.strip(), file=sys.stderr)
    if r.returncode != 0:
        sys.exit(r.returncode)

    # Curate: dated dedup (same payer+amount on different dates are DIFFERENT expenses),
    # Unknown-payer rows excluded from money math with a loud warning (fail-fast, fix in UI).
    parsed = json.loads((outdir / "02_parsed.json").read_text(encoding="utf-8"))
    seen, curated, skipped = set(), [], []
    for e in parsed.get("expenses", []):
        key = (str(e.get("source")), str(e.get("date")), str(e.get("payer")),
               float(e.get("amount", 0)), str(e.get("desc")))
        if key in seen:
            continue
        seen.add(key)
        if str(e.get("payer", "Unknown")).strip().lower() == "unknown" or not str(e.get("payer", "")).strip():
            skipped.append(e)
            continue
        curated.append(e)
    if skipped:
        lost = sum(float(e.get("amount", 0)) for e in skipped)
        print(f"[split] WARNING: {len(skipped)} rows have no payer (Rs.{lost:.0f} excluded) - fix in UI table:",
              file=sys.stderr)
        for e in skipped[:10]:
            print(f"  - {e.get('source')}: {e.get('raw', '')[:80]}", file=sys.stderr)
    (outdir / "03_expenses.json").write_text(
        json.dumps({"count": len(curated), "expenses": curated}, indent=2, ensure_ascii=False), encoding="utf-8")

    members = list(cfg["ROOMMATES"]) or sorted({e["payer"] for e in curated})
    s = compute_settlement(curated, members)
    s["parser"] = parsed.get("parser")
    (outdir / "04_settlement.json").write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")
    text = summary_text(s)
    (outdir / "05_summary.txt").write_text(text, encoding="utf-8")
    print(text)
    print(f"[split] artifacts in {outdir}/ (01..05)")


if __name__ == "__main__":
    main()
