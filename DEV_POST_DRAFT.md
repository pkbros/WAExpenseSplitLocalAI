# DEV post draft — Build for a Friend (Hacktoberfest Weekend Challenge)

## Title options
- I stopped pasting my roommates' grocery chats into ChatGPT — Gemma 4 E2B runs it on my GTX 1650
- Our grocery split lives on my laptop now (local Gemma 4, zero rupees in API bills)

## 1. Who it's for
My roommate [NAME] keeps the grocery list. Every month-end we copy-paste 50+ WhatsApp lines into an online chatbot to split. Amounts, food habits, timings — all on someone else's server.

## 2. What I built (screenshot strip)
Paste chat -> local `gemma4:e2b-it-qat` (4.3GB quant, Ollama, `format=json`) extracts `{payer, amount, desc}` -> editable table -> deterministic Python settles with min-cash-flow ("Priya pays Aman Rs.389").
Repo: [link]. Stack: Ollama v0.35 + Gemma 4 E2B QAT + Streamlit. No API key, works on hostel WiFi offline.

## 3. Demo
GIF: paste 15 Hinglish lines (incl. "Rahul ne 350 diye atta ke liye") -> delete the Rs.1000 rent trap-row live -> settlement cards -> copied summary back to WhatsApp.
Measured: 20/20 deterministic checks green; live run on real export: 9 expenses, Rs.1165, 5 auto-discovered members, zero Unknown payers. Members come from sender tags — nobody types names.

## 4. Why open beat closed (the weighted section)
- Privacy: webcam-grade argument for money — grocery data reveals religion/health/finances. Local = nothing leaves `localhost:11434`.
- Cost: 50 lines x monthly = free forever vs metered tokens.
- Offline: hostel WiFi dies; split doesn't.
- Swappable: `MODEL_NAME=gemma4:e2b-it-q4_K_M` one-line upgrade; Apache 2.0 Gemma 4 (first truly open Gemma) vs custom-terms past. Closed model can't do any of this.
- Small-model honesty: code owns arithmetic + envelopes, model owns wording. One honest warning ("2 items for 1 line") beats a silent wrong split. No regex shadow-implementation to maintain.

## 5. Reaction
"[Roommate quote: e.g. 'delete that rent row felt powerful']." + what broke (bare "meeting at 5" over-parse) and the fix.

## Checklist before submit
- [ ] Public repo link + 3 screenshots/GIF
- [ ] State Gemma 4 + Ollama local (Best Use of Gemma category)
- [ ] Publish before deadline, link challenge post
