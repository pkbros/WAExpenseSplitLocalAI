"""S2 parse core: chat lines -> structured expenses JSON. LLM-only, by design.
CODE owns structure (peels "[date] Sender:" envelopes deterministically so timestamps
can never become amounts). MODEL owns all meaning (who paid what, freeform or export).
No regex fallback, no degraded path: if Ollama is down you get one clear error telling
you exactly how to start it. A wrong money split is worse than no split.
Usage: python parse.py data/01_raw.txt --out data/02_parsed.json
"""
import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import load_config

SYSTEM = (
    "You split grocery expenses from chat lines. Return a JSON OBJECT with exactly two keys: "
    "\"amounts\" (EVERY money number appearing in the message texts, in order, as numbers) and "
    "\"items\" (exactly one item per amount, same order). The two arrays MUST have equal length. "
    "Each item has exactly these keys: {\"payer\": string, \"amount\": number, \"desc\": string, \"date\": string}. "
    "Each input line looks like `N. [YYYY-MM-DD] Sender: message`. Sender and date may be absent on freeform lines. "
    "payer is the Sender name EXACTLY as written when present, otherwise the person named in the message, "
    "otherwise Unknown. NEVER take numbers from the [YYYY-MM-DD] bracket as amounts - amounts come only from the message. "
    "When ONE amount covers several items ('Sabji+atta+kela -->370'), return ONE item with that amount "
    "and the combined desc - NEVER repeat the same amount across items. "
    "desc is short item text. date is the bracket date, or null if absent. "
    "Skip system and chit-chat lines (joined, left, Media omitted, deleted, no amount) by omitting them from BOTH arrays. "
    "Example: '1. [2026-09-28] Prateek Sharma: 100 sabji aata | 2. [2026-09-29] Atul: Sabji --> 40 + 30' -> "
    "{\"amounts\":[100,40,30],\"items\":["
    "{\"payer\":\"Prateek Sharma\",\"amount\":100,\"desc\":\"sabji aata\",\"date\":\"2026-09-28\"},"
    "{\"payer\":\"Atul\",\"amount\":40,\"desc\":\"Sabji\",\"date\":\"2026-09-29\"},"
    "{\"payer\":\"Atul\",\"amount\":30,\"desc\":\"maggi\",\"date\":\"2026-09-29\"}]}"
)

RETRY_NOTE = (
    "Count again: your items array length does not match the money amounts in the lines. "
    "List EVERY money number in \"amounts\" and return exactly one item per amount in \"items\"."
)

WA_BRACKET_RE = re.compile(r"^\[(.+?)\]\s*([^:]+?):\s*(.*)$")
WA_DASH_RE = re.compile(r"^(\d{1,2}/\d{1,2}(?:/\d{2,4})?,?\s+\d{1,2}:\d{2}(?::\d{2})?)\s*[-\u2013\u2014]\s*([^:]+?):\s*(.*)$")
DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?")
SYSTEM_MSG_RE = re.compile(
    r"(?i)(joined|left|added|removed|created|changed|encrypted|media omitted|message was deleted|"
    r"missed (voice|video) call|turned (on|off) disappearing)")
DATE_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

OLLAMA_HINT = (
    "Ollama is not reachable or returned nothing usable.\n"
    "  1. Start it:  Start-Process \"$env:LOCALAPPDATA\\Programs\\Ollama\\ollama app.exe\"\n"
    "  2. Pull the model:  ollama pull gemma4:e2b-it-qat\n"
    "  3. Re-run this command."
)


def parse_wa_date(dstamp):
    """'28/09, 21:30' / '28/09/2026, 21:30:45' -> '2026-09-28'. None if unparseable."""
    if not dstamp:
        return None
    m = DATE_RE.search(dstamp)
    if not m:
        return None
    try:
        d, mo = int(m.group(1)), int(m.group(2))
        y = m.group(3)
        year = int(y) if y else datetime.now().year
        if y and len(y) == 2:
            year += 2000
        if not (1 <= mo <= 12 and 1 <= d <= 31):
            return None
        return f"{year:04d}-{mo:02d}-{d:02d}"
    except (ValueError, TypeError):
        return None


def parse_wa_header(line):
    """Split an optional export envelope. Never fails: plain lines come back unstructured.
    Returns dict(date|None, sender|None, body, structured, system)."""
    line = line.strip()
    sender, dstamp, body, structured = None, None, line, False
    m = WA_BRACKET_RE.match(line) or WA_DASH_RE.match(line)
    if m:
        dstamp, sender, body = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        structured = True
    return {"date": parse_wa_date(dstamp) if structured else None,
            "sender": sender or None, "body": body,
            "structured": structured,
            "system": bool(SYSTEM_MSG_RE.search(body))}


def discover_senders(lines):
    """Ordered unique sender names from structured lines. Empty = freeform paste."""
    seen, out = set(), []
    for raw in lines:
        if not raw.strip():
            continue
        s = parse_wa_header(raw).get("sender")
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def coerce_items(data):
    """Accept list, {"expenses": [...]}, any single-list dict, or a single expense dict."""
    if data is None:
        return []
    if isinstance(data, dict):
        for k in ("expenses", "items", "data", "results", "purchases"):
            if isinstance(data.get(k), list):
                return data[k]
        lists = [v for v in data.values() if isinstance(v, list)]
        if len(lists) == 1:
            return lists[0]
        if any(k in data for k in ("amount", "price", "cost", "payer", "who", "desc", "item", "date")):
            return [data]
        return []
    if isinstance(data, list):
        return data
    return []


def coerce_expense(item, canon):
    if not isinstance(item, dict):
        return None
    amt_raw = item.get("amount", item.get("price", item.get("cost", item.get("rs", 0))))
    payer_raw = item.get("payer", item.get("who", item.get("name", item.get("person", "Unknown"))))
    desc_raw = item.get("desc", item.get("item", item.get("what", item.get("description", "grocery"))))
    try:
        amt = float(amt_raw)
        payer = str(payer_raw).strip() or "Unknown"
        desc = str(desc_raw).strip()[:80] or "grocery"
    except (ValueError, AttributeError):
        return None
    if amt <= 0 or amt > 100000:
        return None
    dt = str(item.get("date") or "").strip()
    if not DATE_ISO_RE.match(dt):
        dt = ""
    for c in canon:
        if payer.lower() == c.lower():
            payer = c
            break
    else:
        # Model often shortens senders ("Atul" for "Atul 2nd Floor Rkgit").
        # Map only on a UNIQUE first-token match; collisions keep model text + UI fixes.
        firsts = {}
        for c in canon:
            firsts.setdefault(c.split()[0].lower(), []).append(c)
        hit = firsts.get(payer.lower(), [])
        payer = hit[0] if len(hit) == 1 else payer[:40]
    return {"payer": payer, "amount": amt, "desc": desc, "date": dt,
            "raw": "", "source": "", "parser": "llm"}


def _counts_match(data, items, nlines):
    """Self-check: model's own enumerated amounts vs returned items. Guards recall
    without any pattern matching on our side. Garbage floods (>3x lines) never match."""
    if not isinstance(data, dict) or not isinstance(data.get("amounts"), list):
        return 1 <= len(items) <= 4 * max(nlines, 1)
    if len(data["amounts"]) > 3 * max(nlines, 1):
        return False
    return len(data["amounts"]) == len(items)


def _chat(client, cfg, prompt_lines, retry=False):
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt_lines}]
    if retry:
        msgs.append({"role": "user", "content": RETRY_NOTE})
    resp = client.chat(
        model=cfg["MODEL_NAME"], messages=msgs, format="json",
        options={"temperature": cfg["LLM_TEMPERATURE"], "num_ctx": cfg["LLM_NUM_CTX"]},
    )
    text = resp.message.content.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


def llm_parse(lines, cfg, batch=1):
    """Local Gemma 4 E2B quant, one line per call (small models drop lines in batches).
    The model first enumerates every amount, then itemizes one row per amount; mismatched
    counts trigger one retry. Returns (expenses, warnings). Raises RuntimeError with setup
    instructions if the model is unreachable or a batch yields nothing usable."""
    import ollama  # lazy: import error itself becomes the actionable message below
    try:
        client = ollama.Client(host=cfg["OLLAMA_HOST"], timeout=cfg["LLM_TIMEOUT_S"])
        client.list()
    except Exception:
        raise RuntimeError(OLLAMA_HINT)
    stripped, orig_no = [], []
    for i, l in enumerate(lines):
        if l.strip():
            stripped.append(l)
            orig_no.append(i + 1)
    # System lines carry no money; drop before batching (code owns structure).
    kept, kept_no = [], []
    for l, n in zip(stripped, orig_no):
        if not parse_wa_header(l)["system"]:
            kept.append(l)
            kept_no.append(n)
    if not kept:
        raise RuntimeError("No expense lines: every line looks like a system message.")
    canon = list(cfg["ROOMMATES"]) or discover_senders(kept)
    infos = [parse_wa_header(l) for l in kept]
    out, warnings = [], []
    for b in range(0, len(kept), batch):
        chunk, chunk_no = kept[b:b + batch], kept_no[b:b + batch]
        ch_infos = infos[b:b + batch]
        prompt_lines = []
        for n, l, inf in zip(chunk_no, chunk, ch_infos):
            if inf["structured"]:
                tag = f"[{inf['date']}] " if inf["date"] else ""
                prompt_lines.append(f"{n}. {tag}{inf['sender']}: {inf['body']}")
            else:
                prompt_lines.append(f"{n}. {l.strip()}")
        user = "Group members: %s\nLines:\n%s" % (
            ", ".join(canon) if canon else "unknown", "\n".join(prompt_lines))
        data, items = None, []
        try:
            data = _chat(client, cfg, user)
            items = [e for e in (coerce_expense(i, canon) for i in coerce_items(data)) if e]
            if not _counts_match(data, items, len(chunk)):
                data = _chat(client, cfg, user, retry=True)
                items = [e for e in (coerce_expense(i, canon) for i in coerce_items(data)) if e]
        except Exception as e:
            raise RuntimeError(OLLAMA_HINT + f"\n(detail: {e})")
        if not items:
            raise RuntimeError(
                f"Model returned nothing usable for lines {chunk_no[0]}-{chunk_no[-1]} after retry.\n" + OLLAMA_HINT)
        if isinstance(data, dict) and isinstance(data.get("amounts"), list) \
                and len(data["amounts"]) != len(items):
            warnings.append(
                f"batch lines {chunk_no[0]}-{chunk_no[-1]}: model saw amounts {data['amounts']} "
                f"but returned {len(items)} items - check the UI table.")
        # Ground rows to source lines when counts align 1:1 (usual case).
        # Otherwise ground what the envelope already tells us (single sender/date),
        # and flag the rest instead of guessing.
        if len(items) == len(chunk):
            for e, l, n, inf in zip(items, chunk, chunk_no, ch_infos):
                e["raw"], e["source"] = l.strip(), f"line:{n}"
                if inf["date"] and not e["date"]:
                    e["date"] = inf["date"]
                if e["payer"] in ("Unknown", "") and inf["sender"]:
                    e["payer"] = inf["sender"]
        else:
            senders = {inf["sender"] for inf in ch_infos if inf["sender"]}
            dates = {inf["date"] for inf in ch_infos if inf["date"]}
            for e in items:
                e["raw"], e["source"] = "", f"lines:{chunk_no[0]}-{chunk_no[-1]}"
                if len(senders) == 1 and e["payer"] in ("Unknown", ""):
                    e["payer"] = next(iter(senders))
                if len(dates) == 1 and not e["date"]:
                    e["date"] = next(iter(dates))
            warnings.append(
                f"batch lines {chunk_no[0]}-{chunk_no[-1]}: model returned {len(items)} items "
                f"for {len(chunk)} lines - check descs in the UI table.")
        for e in items:
            if not e["date"]:
                e["date"] = date.today().isoformat()
            out.append(e)
    out.sort(key=lambda e: int(re.sub(r"\D", "", e.get("source", "0").split("-")[0]) or 0))
    return out, warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="input .txt: WA export and/or freeform lines")
    ap.add_argument("--out", default="data/02_parsed.json")
    args = ap.parse_args()
    cfg = load_config()
    lines = Path(args.input).read_text(encoding="utf-8").splitlines()
    lines = [l for l in lines if l.strip()]
    if not lines:
        print("no input lines", file=sys.stderr)
        sys.exit(2)
    try:
        expenses, warnings = llm_parse(lines, cfg)
    except RuntimeError as e:
        print(f"[parse] FAILED\n{e}", file=sys.stderr)
        sys.exit(3)
    for w in warnings:
        print(f"[parse] warning: {w}", file=sys.stderr)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"parser": "llm:" + cfg["MODEL_NAME"], "count": len(expenses),
                                    "expenses": expenses}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"parsed {len(expenses)} expenses via llm:{cfg['MODEL_NAME']} -> {out_path}")


if __name__ == "__main__":
    main()
