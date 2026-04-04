# TaxTrack Pro

Flask-based mobile-first prototype for preparing ITR-3 from imported AIS/26AS-style data.

## Prerequisites
- Python 3.10+
- `pip`

## Run locally
1. Create and activate a virtual environment.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies.
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. (Optional) create a local `.env` file.
   ```bash
   cp .env.example .env
   ```
4. Start the Flask app.
   ```bash
   python app.py
   ```
5. Open in browser:
   - http://127.0.0.1:5000

## Notes
- On first run, SQLite DB `taxtrack_pro.db` is created automatically.
- A demo user (`PAN: DEMO0000AA`) is seeded automatically.
