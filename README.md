# Copper Per Section Report

Python + Streamlit project for cleaning up data pulled from Egnyte and producing a report.

## Structure

- `data/raw/` — original files as pulled from Egnyte, untouched
- `data/processed/` — cleaned/merged output, ready for reporting
- `src/` — cleaning and processing scripts (e.g. `clean.py`, `load.py`)
- `app/` — Streamlit app (e.g. `app.py` as entry point)
- `requirements.txt` — Python dependencies
- `.gitignore` — excludes data files and local env from version control

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Next steps

1. Drop raw files into `data/raw/`
2. Write cleaning logic in `src/`
3. Build the Streamlit report in `app/app.py`
4. Run with `streamlit run app/app.py`
