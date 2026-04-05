# TaxTrack Pro

Flask-based mobile-first prototype for preparing ITR-3 from imported AIS/26AS-style data.

## One-click start (for each platform)
Run these from inside `taxtrack_pro/`.

### Replit (one click)
- Replit Run button is configured via `.replit`.
- Manual command:
  ```bash
  bash one_click/replit_start.sh
  ```

### Render / Railway (one click shell command)
```bash
bash one_click/cloud_start.sh
```
(For normal deploy UI, `Procfile` already uses Gunicorn.)

### Termux Android (one click)
```bash
bash one_click/termux_start.sh
```

---

## Run entirely from mobile (no desktop)
You have 3 practical options:

### Option A (easiest): Replit from phone browser
1. Open **replit.com** on mobile browser and create/import this project.
2. Tap **Run** (uses `.replit`).
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
   bash one_click/termux_start.sh
   ```
3. Open `http://127.0.0.1:5000` on same phone.

## Notes
- App binds to `0.0.0.0` and reads `PORT` from environment (default `5000`).
- On first run, SQLite DB `taxtrack_pro.db` is created automatically.
- A demo user (`PAN: DEMO0000AA`) is seeded automatically.
