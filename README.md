# WAExpenseSplitLocalAI

Split shared grocery spending without pasting your group's money chats into a cloud chatbot.
Paste a WhatsApp export (and/or freeform lines) → a **local open-weight model** reads every
line → you correct anything in a table → deterministic Python computes who pays whom.
No API key, no account, no data leaves your laptop.

Built with [Gemma 4 E2B](https://ai.google.dev/gemma) (Apache 2.0) running locally via
[Ollama](https://ollama.com). Originally made for a Hacktoberfest "Build for a Friend" entry:
month-end grocery splits for roommates, parsed on-device for privacy.

## Why local

Grocery + money chats reveal food habits, routines, locations, and financial state.
Pasting them into an online AI sends all of that to someone else's server. Running the
model on your own machine means:

- **Private** — traffic never leaves `localhost:11434`.
- **Free** — zero per-parse cost, unlimited re-runs.
- **Offline** — works on hostel WiFi or no WiFi after a one-time ~4.3 GB model download.
- **Swappable** — one `.env` line changes the model (`gemma4:e2b-it-qat` ↔ `gemma4:e2b-it-q4_K_M`).

## Demo

```
paste:
  [28/09, 21:30] Aarav Mehta: 100 sabji aata
  [29/09, 23:43] Diya 2nd Floor Hostel: Sabji+jeera+ maggi--> 40 + 30
  Rohan paid 200 for milk and bread
        ↓  (local model, one call per line)
table:  payer ↓ | amount | desc | date   (editable — fix anything here)
        ↓  (pure Python, the model never does arithmetic)
Total Rs.1165 / 5 = Rs.233 each
- Aarav Mehta pays Diya 2nd Floor Hostel Rs.98
- Kabir Nath Hostel pays Diya 2nd Floor Hostel Rs.93
- ...
```

Mixed pastes work: export lines and freeform/Hinglish lines in one go. Members are taken
from the model's payers — nobody types a roster. Same person on different dates stays
separate (two `70 daal` entries a week apart are two expenses).

## Requirements

| What | Tested on | Notes |
|---|---|---|
| OS | Windows 11 | macOS/Linux work via Ollama + Python too (paths differ) |
| Python | 3.13 | `pip install -r requirements.txt` (`streamlit`, `ollama`, `python-dotenv`) |
| Ollama | 0.35+ | https://ollama.com/download |
| Model | `gemma4:e2b-it-qat` (~4.3 GB) | `ollama pull gemma4:e2b-it-qat` |
| Hardware | 4 GB VRAM laptop GPU works | Model runs as GPU+CPU hybrid (30/36 layers on a GTX 1650); more VRAM/RAM = faster |

## Quickstart

```powershell
# 1. Install Ollama 0.35+ from https://ollama.com/download, then pull the model (one time)
ollama pull gemma4:e2b-it-qat

# 2. Install Python deps
pip install -r requirements.txt

# 3. Configure (optional — defaults work)
copy .env.example .env

# 4a. Web UI
streamlit run app.py

# 4b. Or CLI only (no browser needed)
python split.py sample_inputs.txt --out data
```

`sample_inputs.txt` contains fictional people in both formats so you can try it instantly.
Your real chats are pasted at runtime and never committed (`.env`, `data/` are gitignored).

## Usage

**UI (`streamlit run app.py`):** paste lines → *Split locally* → fix names/amounts/dates in the
table (delete non-expense rows, set any `Unknown` payer) → settlements + copyable summary.
The caption under the table shows which members the model found.

**CLI:** `python split.py <chat.txt> --out data` writes staged artifacts:

```
data/01_raw.txt          your paste, verbatim
data/02_parsed.json      model output per line (with parser tags + raw source)
data/03_expenses.json    curated (deduped, Unknown-payer rows excluded with a warning)
data/04_settlement.json  totals, per-person share, minimal transfers
data/05_summary.txt      paste-back-to-WhatsApp text
```

Individual stages for debugging: `python parse.py <in> --out <json>`,
`python settle.py data/03_expenses.json --out data/04_settlement.json`,
`python check.py` (20 deterministic checks — settle math, envelope parsing, output validation).

### Configuration (`.env`)

| Key | Default | Meaning |
|---|---|---|
| `MODEL_NAME` | `gemma4:e2b-it-qat` | Ollama model tag. Swap freely, e.g. `gemma4:e2b-it-q4_K_M` |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server |
| `LLM_TEMPERATURE` | `0` | Deterministic parsing |
| `LLM_NUM_CTX` | `2048` | Context window (short prompts; smaller = less VRAM) |
| `LLM_TIMEOUT_S` | `90` | Per-call timeout |
| `ROOMMATES` | *(empty)* | Fixed roster override. Empty = members come from the model's payers |

## How it works

- **Code owns structure.** Export envelopes (`[28/09, 21:30] Name: …`, Android dash form)
  are peeled deterministically, so timestamps can never be mistaken for amounts.
- **Model owns meaning.** One Ollama call per line (small models drop lines in batches).
  The model first enumerates every amount it sees, then returns one item per amount —
  its own count is checked and retried once on mismatch. Anything still off is flagged
  as a warning instead of silently patched.
- **Python owns money.** Totals, equal shares, and minimal settlements are plain code;
  the model never does arithmetic. `Unknown`-payer rows are excluded from the math with
  a loud warning, not folded in.

Honest limits: expect roughly 10–20 seconds per line on a 4 GB laptop GPU (an 8-line
paste takes a couple of minutes); a multi-amount line occasionally needs a desc touch-up
in the table. Both are visible in the UI before money is computed.

## Privacy

Real chat data only ever exists in your paste box, your `data/` folder, and localhost
HTTP calls to Ollama. Nothing is logged, uploaded, or committed — `.gitignore` covers
`.env`, `data/`, and PDFs. The repo's sample data is fictional.

## Contributing

Small, reviewable PRs: one concern per change, `python check.py` green (20/20), and a
live `split.py` run pasted into the PR if parsing behavior changed. See `TRACKER.md`
for the decisions log and `MANUAL.md` for the longer walkthrough.

## License

TBD — pick one (MIT or Apache-2.0 suggested) and add a `LICENSE` file before publishing.

## Credits

- [Google DeepMind Gemma 4](https://ai.google.dev/gemma) — open weights, Apache 2.0
- [Ollama](https://ollama.com) — local inference server
- [Streamlit](https://streamlit.io) — UI
