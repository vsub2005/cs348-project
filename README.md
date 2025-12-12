CS348 Project — Intramural League (Flask + SQLAlchemy + React)

Stack: Python 3.12, Flask, SQLAlchemy, SQLite, React (Vite).

Structure
cs348-project/
├─ server/
│  ├─ app.py
│  ├─ models.py
│  ├─ requirements.txt
│  ├─ seed.py
│  └─ instance/
└─ client/
   ├─ src/App.jsx
   ├─ package.json
   └─ vite.config.js

Run

Backend
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py

Frontend
cd ../client
npm install
npm run dev

Endpoints
GET /api/sports
GET /api/teams?sport_id=...
GET /api/venues
GET /api/games?sport_id=&team_id=&from=&to=
POST /api/games
PUT /api/games/<id>
DELETE /api/games/<id>
GET /api/report/games?sport_id=&team_id=&from=&to=

Stage 1 and 2
Dynamic dropdowns from DB
Create, update, delete a game
Report with filters and stats

Stage 3
All DB access via SQLAlchemy ORM
Indexes:
ix_game_sport_date (Game.sport_id, Game.date)
ix_game_home_date (Game.home_team_id, Game.date)
ix_game_away_date (Game.away_team_id, Game.date)
ix_team_sport (Team.sport_id)
Transactions on writes
Optimistic concurrency:
Game.row_version integer
Client sends row_version on update
Server compares, 409 on mismatch, increments on success
