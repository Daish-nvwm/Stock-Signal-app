# Personal Signal Alerts (Starter Kit)

This is a starter project for a personal (self-use) stock signal + alert system.
It is **configuration-driven**: tweak parameters in `config/` without changing core code.

## Quick start (Windows / macOS / Linux)

1) Install Python 3.11+
2) Create and activate a virtualenv:

Windows PowerShell:
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1

macOS/Linux:
    python3 -m venv .venv
    source .venv/bin/activate

3) Install dependencies:
    pip install -r requirements.txt

4) Run demo (generates synthetic bars and prints sample alerts):
    python -m src.main --demo

## Next step
Replace `src/data/loader.py` to load your real market data (bars) and store it under `data/processed/`.
