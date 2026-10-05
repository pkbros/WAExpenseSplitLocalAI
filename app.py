"""S5 UI: thin wrapper over parse/settle core. Heavy imports only here.
Members auto-detected from export senders; freeform lines use the override box."""
import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from config import load_config
from parse import OLLAMA_HINT, llm_parse
from settle import compute_settlement, summary_text

cfg = load_config()
st.set_page_config(page_title="WAExpenseSplitLocalAI", layout="centered")
st.title("Local expense splitter (Gemma 4 E2B, offline)")
st.caption(f"Model: {cfg['MODEL_NAME']} via Ollama localhost - no data leaves this laptop.")

raw = st.text_area(
    "Paste WhatsApp export and/or freeform lines (mixed is fine)", value="",
    height=220,
    placeholder="[28/09, 21:30] Aarav: 100 sabji aata\nDiya: maggi --> 30\nRohan paid 200 for milk",
)
if not raw.strip():
    st.info("Paste your chat export above, then split. Nothing is prefilled - your data stays yours.")

lines = [l for l in raw.splitlines() if l.strip()]

if st.button("Split locally"):
    if not lines:
        st.warning("Paste at least one line.")
        st.stop()
    with st.spinner("Parsing on-device..."):
        try:
            expenses, warnings = llm_parse(lines, cfg)
            parser = "llm:" + cfg["MODEL_NAME"]
        except RuntimeError as e:
            st.error("Local model unavailable")
            st.code(str(e))
            st.stop()
    for w in warnings:
        st.warning(w)
    st.caption(f"Parser: {parser} - fix any row below before settling.")
    edited = st.data_editor(
        [{"payer": e["payer"], "amount": e["amount"], "desc": e["desc"], "date": e.get("date", "")}
         for e in expenses],
        num_rows="dynamic", use_container_width=True, key="ed",
    )
    clean, unknown_n, unknown_rs = [], 0, 0.0
    for r in edited:
        try:
            amt = float(r.get("amount", 0))
        except (ValueError, TypeError):
            continue
        if amt <= 0:
            continue
        payer = str(r.get("payer", "Unknown")).strip()[:40] or "Unknown"
        if payer.lower() == "unknown":
            unknown_n += 1
            unknown_rs += amt
            continue
        clean.append({"payer": payer, "amount": amt,
                      "desc": str(r.get("desc", ""))[:80],
                      "date": str(r.get("date", ""))})
    if unknown_n:
        st.warning(f"{unknown_n} rows have no payer (Rs.{unknown_rs:.0f} excluded) - set payer above.")
    eff_members = sorted({e["payer"] for e in clean})
    st.caption(f"Members (from model): {', '.join(eff_members)} - fix names in the table if needed.")
    if clean and eff_members:
        s = compute_settlement(clean, eff_members)
        st.subheader(f"Total Rs.{s['grand_total']:.0f} = Rs.{s['share_each']:.0f} each")
        cols = st.columns(len(s["members"]) or 1)
        for c, m in zip(cols, s["members"]):
            c.metric(m, f"paid {s['paid'][m]:.0f}", f"net {s['net'][m]:+.0f}")
        if s["transfers"]:
            st.subheader("Settle")
            for t in s["transfers"]:
                st.success(f"{t['from']} pays {t['to']} Rs.{t['amount']:.0f}")
        else:
            st.info("All settled.")
        txt = summary_text(s)
        st.code(txt)
        Path("data").mkdir(exist_ok=True)
        Path("data/04_settlement.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
