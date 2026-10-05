"""Single switchboard. CLIs take paths/actions only; all tuning lives in .env."""
import os
from pathlib import Path

def load_config(env_path="D:\\projects\\WAExpenseSplitLocalAI\\.env"):
    # Minimal .env loader (no dep needed for CLI core; dotenv only for UI convenience)
    if Path(env_path).exists():
        for line in Path(env_path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
    return {
        "MODEL_NAME": os.getenv("MODEL_NAME", "gemma4:e2b-it-qat"),
        "FALLBACK_MODEL": "gemma4:e2b-it-q4_K_M",
        "OLLAMA_HOST": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        "LLM_TEMPERATURE": float(os.getenv("LLM_TEMPERATURE", "0")),
        "LLM_NUM_CTX": int(os.getenv("LLM_NUM_CTX", "2048")),
        "LLM_TIMEOUT_S": int(os.getenv("LLM_TIMEOUT_S", "90")),
        "ROOMMATES": [r.strip() for r in os.getenv("ROOMMATES", "Aman,Rahul,Priya").split(",") if r.strip()],
        "DATA_DIR": os.getenv("DATA_DIR", "./data"),
    }
