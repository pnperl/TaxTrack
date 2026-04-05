# TaxTrack Pro

Flask-based mobile-first prototype for preparing ITR-3 from imported AIS/26AS-style data.

## One-click start (for each platform)
If your terminal is already in `taxtrack_pro/`, use:

### Replit (one click)
```bash
bash start_replit.sh
```

### Render / Railway (one click shell command)
```bash
bash start_cloud.sh
```

### Termux Android (one click)
```bash
bash start_termux.sh
```

If you are in the parent repo directory, prefix with `taxtrack_pro/` (example: `bash taxtrack_pro/start_replit.sh`).

---

## Run entirely from mobile (no desktop)
You have 3 practical options:

### Option A (easiest): Replit from phone browser
1. Open **replit.com** on mobile browser and create/import this project.
2. Tap **Run** (uses `.replit` → `start_replit.sh`).
3. Open the public Replit URL on phone.

### Option B: Render / Railway deployment from phone
1. Push project to GitHub.
2. From phone, create a web service from repo.
3. Configure:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn -w 2 -b 0.0.0.0:$PORT app:app`
4. Open generated HTTPS URL on mobile.

### Option C: Android Termux (local on phone)
1. Install Termux.
2. Clone repo and run:
   ```bash
   cd TaxTrack/taxtrack_pro
   bash start_termux.sh
   ```
3. Open `http://127.0.0.1:5000` on same phone.

## Notes
- App binds to `0.0.0.0` and reads `PORT` from environment (default `5000`).
- On first run, SQLite DB `taxtrack_pro.db` is created automatically.
- A demo user (`PAN: DEMO0000AA`) is seeded automatically.
