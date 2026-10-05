# TRACKER — WAExpenseSplitLocalAI (single source of truth)

## Status (2026-10-05)
- Phase: BUILD — S0 in progress
- Current: creating memory docs + config, then core CLI
- Next: Ollama install + `gemma4:e2b-it-qat` pull (manual, see Blocked)

## Done
- [2026-10-05] Spec locked: local roommate grocery splitter, paste + manual, LLM parses, Python settles
- [2026-10-05] Hardware checked: Win11, Ryzen 5 5600H, ~20GB RAM, GTX 1650 4GB, C:22GB/D:318GB, Py3.13, no Ollama
- [2026-10-05] Research: Gemma 4 (Apache 2.0, Apr+Jun 2026) on Ollama, 51 tags verified; Ollama v0.35.0
- [2026-10-05] S0+S1 done: TRACKER, .env(.example), README, requirements, config.py, sample_inputs.txt
- [2026-10-05] S2+S3+S4 done: parse.py (llm+regex, payer-inherit fix), settle.py, split.py
- [2026-10-05] S5 done: app.py Streamlit wrapper (syntax + imports OK)
- [2026-10-05] S6 partial: check.py 11/11 green; split --no-llm verified (17 expenses, Aman 2169/Priya 1299/Rahul 1595); deps installed (streamlit 1.65, ollama 0.6.3); MANUAL.md + DEV_POST_DRAFT.md written
- [2026-10-05] S6 DONE: Ollama 0.35.1 installed via winget; OLLAMA_MODELS=D:/ollama_models; gemma4:e2b-it-qat pulled (4.3GB)
- [2026-10-05] LLM path verified live on GTX 1650: split.py (no flags) -> 17 expenses via llm:gemma4:e2b-it-qat; settlement Aman 2169/Priya 1299/Rahul 1595; check.py 11/11; Streamlit UI HTTP 200
- [2026-10-05] GPU diagnosis: ollama ps showed 63%/37% CPU/GPU (not 0%); nvidia-smi 2539/4096MB used, driver 595.79 OK. Cause = VRAM wall (4.3GB model vs ~1.5GB free), not config. Set LLM_NUM_CTX 4096->2048, server OLLAMA_KV_CACHE_TYPE=q8_0 + OLLAMA_FLASH_ATTENTION=1, restarted tray; new split run CONTEXT 2048, offload 62%/38%, GPU util spikes 65% during generation. 100% GPU needs ~4.5GB free VRAM — close browser/Discord etc. to raise share; re-check with `ollama ps`.
- [2026-10-05] server.log confirms CUDA0 = GTX 1650, 30/36 layers offloaded (1195MB GPU / 2299MB host). iGPU not involved. Steady state accepted: 4GB dGPU + CPU hybrid is the correct operating point; no further tuning.
- [2026-10-05] SUPERSEDE: regex fallback + top-up DELETED per user (a silent worse path is not a fallback). parse.py is LLM-only; Ollama-down exits 3 with setup steps. Skill project-discipline §6 amended same day: fail-fast default, fallbacks opt-in only.
- [2026-10-05] LLM-only verified live on real export+freeform mix: batch=1, amounts/items self-check prompt, no-repeat-amounts rule, unique first-token sender canon. Result: 9 expenses, Rs.1165, 5 members, 0 Unknown, 1 honest warning (line 2 descs). run1.pdf garbage (Unknown pays, timestamp amounts) resolved: root causes were raw timestamps fed to model + ROOMMATES-gated payer search.
- [2026-10-05] Members input field REMOVED per user (silent guessing backfires). Members = model's payers, shown as caption, corrected in edit table. .env ROOMMATES stays as optional fixed-roster override. Repo de-identified for GitHub: fictional sample, empty textarea + placeholder, .gitignore (.env, data/, pdfs), run1.pdf deleted. Re-verified on fictional data: 9/Rs.1165/5 members, UI HTTP 200.
- [2026-10-05] README rewritten for open source (usage, config table, architecture, privacy, contributing). .env.example cleaned (no fallback mention, empty ROOMMATES, dropped unread keys). check.py 20/20.
- [2026-10-05] Fixed lying error: empty-model-result blamed Ollama-down. Now per-batch failures warn+skip, OLLAMA_HINT only on real connection failure, honest "reachable but found nothing" otherwise. Prompt now keeps person-to-person transfers as rows (desc names receiver). Verified on user's 8 lines: 9 expenses incl. 100 sent + 220 udhaar, 20/20 green.

## In-progress
- S0: TRACKER.md / .env.example / README skeleton

## Next
- S1 config + sample_inputs.txt
- S2 parse core, S3 settle core, S4 orchestrator, S5 UI, S6 verify + DEV draft

## Decisions log (append-only)
- [2026-10-05] Model = `gemma4:e2b-it-qat` (4.3GB) primary, `gemma4:e2b-it-q4_K_M` (4.6GB) fallback. Rationale: smallest E2B quant, QAT preserves JSON accuracy at 4-bit, fits GTX 1650 4GB + fast download; Q8/BF16/MLX/NVFP4 rejected (too big / wrong HW).
- [2026-10-05] Terminal core first, Streamlit last. Rationale: skill §7, debug parse/settle without GUI.
- [2026-10-05] Model does meaning (parse), code does determinism (settle). Rationale: never let LLM do arithmetic.
- [2026-10-05] Staged artifacts on disk: 01_raw.txt -> 02_parsed.json -> 03_expenses.json -> 04_settlement.json. Additive/immutable, idempotent reruns.
- [2026-10-05] LLM batching (5 lines/call) + per-row provenance + regex top-up for missed amounts. Rationale: E2B QAT returns 1 object on 15-line inputs, renames keys (item/price), drops payers; batching + tolerant coerce + top-up gives 17/17 recall with honest parser tags. Symptom->cause->fix->proof logged.
- [2026-10-05] Residual documented: regex over-parses bare numbers ("meeting at 5"); LLM skips them; UI delete is the curation step. Not fixed in code (would break "Priya 89 curd" style).

## Task log
- [2026-10-05] Session start: empty repo, plan->build switch, skill project-discipline loaded.

## Blocked / needs human
- (was: Ollama install + pull — DONE above, no longer blocked)
- 10-15 real anonymized grocery lines + the one roommate's first name for DEV post framing (sample data works, real chat is better)
- 3 screenshots/GIF from `streamlit run app.py` + DEV publish + repo public link
