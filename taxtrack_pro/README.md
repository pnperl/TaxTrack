# TaxTrack Pro

Flask-based mobile-first prototype for preparing ITR-3 from imported AIS/26AS-style data.

## Run entirely from mobile (no desktop)
You have 3 practical options:

### Option A (easiest): Replit from phone browser
1. Open **replit.com** on mobile browser and create a new Python Repl.
2. Upload this `taxtrack_pro` folder.
3. In Replit shell, run:
   ```bash
   pip install -r requirements.txt
   gunicorn -w 2 -b 0.0.0.0:$PORT app:app
   ```
4. Open the Replit web URL shown by Replit (works directly on phone).

### Option B: Render / Railway deployment from phone
1. Push project to GitHub.
2. From your phone, open Render/Railway dashboard and create a new web service from repo.
3. Configure:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn -w 2 -b 0.0.0.0:$PORT app:app`
4. Open generated HTTPS URL on mobile.

### Option C: Android Termux (local on phone)
1. Install Termux.
2. Clone repo and run:
   ```bash
   pkg update -y
   pkg install -y python git
   cd TaxTrack/taxtrack_pro
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python app.py
   ```
3. Open `http://127.0.0.1:5000` on the same phone.

---

## Desktop quick start (optional)
```bash
cd taxtrack_pro
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env   # optional
python app.py
```

Open in browser: http://127.0.0.1:5000

## Notes
- App binds to `0.0.0.0` and reads `PORT` from environment (default `5000`).
- On first run, SQLite DB `taxtrack_pro.db` is created automatically.
- A demo user (`PAN: DEMO0000AA`) is seeded automatically.
