# MANUAL — WAExpenseSplitLocalAI

## Setup
1. Install Ollama v0.35+: `winget install -e --id Ollama.Ollama` or https://ollama.com/download
   - Move models to D:: `[Environment]::SetEnvironmentVariable("OLLAMA_MODELS","D:\ollama_models","User")`, restart Ollama.
2. `ollama pull gemma4:e2b-it-qat` (~4.3GB). Fallback: `ollama pull gemma4:e2b-it-q4_K_M`
3. `pip install -r requirements.txt` ✅ done (streamlit 1.65, ollama 0.6.3)
4. `copy .env.example .env` ✅ done — `ROOMMATES` stays empty (members come from the model's payers; set it only to force a fixed roster).

## Command reference
- `python check.py` — 20 deterministic checks (settle math + envelope parsing + output coercion). Must be 20/20. No Ollama needed.
- `python split.py sample_inputs.txt --out data` — full LLM path (needs Ollama + model). Verified: 9 expenses, Rs.1165 total, 5 auto-discovered members.
- `python parse.py <in.txt> --out <json>` — stage debug.
- `python settle.py data/03_expenses.json --out data/04_settlement.json` — stage debug.
- `streamlit run app.py` — UI (paste -> fix table -> settle -> copy summary).

## Walkthrough (demo script, 60 sec)
1. Paste export lines (nothing prefilled — placeholder shows the shape). Click Split locally.
2. Members appear from the model's payers; fix any name/row in the edit table (e.g. merge duplicate spellings).
3. Show metrics + settlement cards + copied summary back to WhatsApp.

## Troubleshooting
- `ollama: not recognized` -> install Ollama / reopen terminal.
- `[parse] FAILED` with setup steps -> start the Ollama app + `ollama pull gemma4:e2b-it-qat`. No fallback exists by design; fix the model, not the data.
- `Unknown` payer -> line had no sender and named nobody; set it in the table.
- Model warning "returned N items for M lines" -> check that batch's descs in the table before settling.
- Members wrong -> edit the auto-detected members box (senders come from export tags).
