# CS348 Project — Intramural League (Flask + SQLAlchemy + React)

A small intramural sports app to manage games and generate reports.  
Backend: Flask + SQLAlchemy (SQLite). Frontend: React (Vite).

## Tech Stack
- Python 3.12, Flask, Flask-CORS, SQLAlchemy, SQLite  
- Node 18+, React, Vite

## Project Structure
```text
cs348-project/
├─ server/
│ ├─ app.py
│ ├─ models.py
│ ├─ requirements.txt
│ ├─ seed.py
│ └─ instance/ # holds dev.db (auto-created)
└─ client/
├─ src/App.jsx
├─ package.json
└─ vite.config.js
```


## Quick Start

### Backend
```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
### Frontend
```bash
cd ../client
npm install
npm run dev
```

## API Endpoints
```text
- GET /api/sports
- GET /api/teams?sport_id=...
- GET /api/venues
- GET /api/games?sport_id=&team_id=&from=&to=
- POST /api/games
- PUT /api/games/<id>
- DELETE /api/games/<id>
- GET /api/report/games?sport_id=&team_id=&from=&to=
```