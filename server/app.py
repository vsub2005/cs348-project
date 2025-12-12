# server/app.py
from datetime import datetime, date, time
from typing import Optional

import os
from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from sqlalchemy import text

from models import db, Sport, Team, Venue, Game

# App + DB setup
app = Flask(__name__)
CORS(app)

# Ensure we always use instance/dev.db as the db file
os.makedirs(app.instance_path, exist_ok=True)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(app.instance_path, "dev.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

def _ensure_row_version_column():
    """Runtime migration: add game.row_version if missing (safe in SQLite)."""
    with app.app_context():
        with db.engine.begin() as conn:
            cols = conn.execute(text("PRAGMA table_info('game');")).fetchall()
            names = {c[1] for c in cols}  # (cid, name, type, notnull, dflt_value, pk)
            if "row_version" not in names:
                conn.execute(text("ALTER TABLE game ADD COLUMN row_version INTEGER NOT NULL DEFAULT 0;"))

with app.app_context():
    db.create_all()
    _ensure_row_version_column()

# Helpers
def parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()

def parse_time(s: Optional[str]) -> Optional[time]:
    if not s:
        return None
    return datetime.strptime(s, "%H:%M").time()

def game_to_dict(g: Game):
    return {
        "id": g.id,
        "sport_id": g.sport_id,
        "home_team_id": g.home_team_id,
        "away_team_id": g.away_team_id,
        "venue_id": g.venue_id,
        "date": g.date.isoformat(),
        "time": g.time.strftime("%H:%M"),
        "home_score": g.home_score,
        "away_score": g.away_score,
        "status": g.status,
        "created_at": g.created_at.isoformat(),
        "row_version": getattr(g, "row_version", 0),
    }

def team_to_dict(t: Team):
    return {"id": t.id, "sport_id": t.sport_id, "name": t.name}

def sport_to_dict(s: Sport):
    return {"id": s.id, "name": s.name}

def venue_to_dict(v: Venue):
    return {"id": v.id, "name": v.name, "location": v.location}

# Show that the API is alive
@app.get("/api/hello")
def hello():
    return jsonify(message="Sports API is alive", serverTime=datetime.utcnow().isoformat())

# Referencing data from tables
@app.get("/api/sports")
def list_sports():
    rows = Sport.query.order_by(Sport.name.asc()).all()
    return jsonify([sport_to_dict(s) for s in rows])

@app.get("/api/venues")
def list_venues():
    rows = Venue.query.order_by(Venue.name.asc()).all()
    return jsonify([venue_to_dict(v) for v in rows])

@app.get("/api/teams")
def list_teams():
    sport_id = request.args.get("sport_id", type=int)
    q = Team.query
    if sport_id:
        q = q.filter(Team.sport_id == sport_id)
    rows = q.order_by(Team.name.asc()).all()
    return jsonify([team_to_dict(t) for t in rows])

# Games CRUD
@app.get("/api/games")
def list_games():
    sport_id = request.args.get("sport_id", type=int)
    team_id  = request.args.get("team_id", type=int)
    d_from   = parse_date(request.args.get("from"))
    d_to     = parse_date(request.args.get("to"))

    q = Game.query
    if sport_id:
        q = q.filter(Game.sport_id == sport_id)
    if team_id:
        q = q.filter((Game.home_team_id == team_id) | (Game.away_team_id == team_id))
    if d_from:
        q = q.filter(Game.date >= d_from)
    if d_to:
        q = q.filter(Game.date <= d_to)

    rows = q.order_by(Game.date.desc(), Game.time.desc()).all()
    return jsonify([game_to_dict(g) for g in rows])

@app.get("/api/games/<int:gid>")
def get_game(gid: int):
    g = Game.query.get_or_404(gid)
    return jsonify(game_to_dict(g))

@app.post("/api/games")
def create_game():
    data = request.get_json(force=True)
    sport_id = data.get("sport_id")
    home_team_id = data.get("home_team_id")
    away_team_id = data.get("away_team_id")
    d = parse_date(data.get("date"))
    t = parse_time(data.get("time"))
    if not all([sport_id, home_team_id, away_team_id, d, t]):
        abort(400, description="Missing required fields: sport_id, home_team_id, away_team_id, date, time")

    with db.session.begin():  # create transaction
        g = Game(
            sport_id=sport_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            venue_id=data.get("venue_id"),
            date=d,
            time=t,
            home_score=data.get("home_score"),
            away_score=data.get("away_score"),
            status=data.get("status") or "scheduled",
        )
        db.session.add(g)

    return jsonify(game_to_dict(g)), 201

@app.put("/api/games/<int:gid>")
def update_game(gid: int):
    data = request.get_json(force=True)

    # Require row_version
    if "row_version" not in data:
        abort(400, description="row_version is required for updates")

    with db.session.begin():
        g = Game.query.get(gid)
        if not g:
            abort(404, description="Game not found")

        # Concurrency check
        current = getattr(g, "row_version", 0)
        if data["row_version"] != current:
            return jsonify({
                "error": "conflict",
                "message": "Stale data. Reload and try again.",
                "current_row_version": current
            }), 409

        # Apply updates
        if "sport_id" in data: g.sport_id = data["sport_id"]
        if "home_team_id" in data: g.home_team_id = data["home_team_id"]
        if "away_team_id" in data: g.away_team_id = data["away_team_id"]
        if "venue_id" in data: g.venue_id = data["venue_id"]
        if "date" in data and data["date"]: g.date = parse_date(data["date"])
        if "time" in data and data["time"]: g.time = parse_time(data["time"])
        if "home_score" in data: g.home_score = data["home_score"]
        if "away_score" in data: g.away_score = data["away_score"]
        if "status" in data and data["status"]: g.status = data["status"]

        # Bump version
        setattr(g, "row_version", current + 1)

    return jsonify(game_to_dict(g))

@app.delete("/api/games/<int:gid>")
def delete_game(gid: int):
    data = request.get_json(silent=True) or {}
    expected = data.get("row_version", None)

    with db.session.begin():
        g = Game.query.get(gid)
        if not g:
            abort(404, description="Game not found")

        if expected is not None:
            current = getattr(g, "row_version", 0)
            if expected != current:
                return jsonify({
                    "error": "conflict",
                    "message": "Stale data. Reload and try again.",
                    "current_row_version": current
                }), 409

        db.session.delete(g)

    return jsonify({"ok": True})

# Report filtering
@app.get("/api/report/games")
def report_games():
    sport_id = request.args.get("sport_id", type=int)
    team_id  = request.args.get("team_id", type=int)
    d_from   = parse_date(request.args.get("from"))
    d_to     = parse_date(request.args.get("to"))

    q = Game.query
    if sport_id:
        q = q.filter(Game.sport_id == sport_id)
    if team_id:
        q = q.filter((Game.home_team_id == team_id) | (Game.away_team_id == team_id))
    if d_from:
        q = q.filter(Game.date >= d_from)
    if d_to:
        q = q.filter(Game.date <= d_to)

    rows = q.order_by(Game.date.desc(), Game.time.desc()).all()
    data = [game_to_dict(g) for g in rows]

    # Basic stats
    games_count = len(data)
    finals = [r for r in data if r["status"] == "final"]
    finals_count = len(finals)

    total_points = 0
    counted = 0
    for r in finals:
        hs, as_ = r["home_score"], r["away_score"]
        if hs is not None and as_ is not None:
            total_points += (hs + as_)
            counted += 1
    avg_points_per_final = (total_points / counted) if counted > 0 else None

    win_rate = None
    if team_id:
        wins_for_team = 0
        games_for_team = 0
        for r in finals:
            hs, as_ = r["home_score"], r["away_score"]
            if hs is None or as_ is None:
                continue
            if r["home_team_id"] == team_id or r["away_team_id"] == team_id:
                games_for_team += 1
                if r["home_team_id"] == team_id and hs > as_:
                    wins_for_team += 1
                if r["away_team_id"] == team_id and as_ > hs:
                    wins_for_team += 1
        if games_for_team > 0:
            win_rate = wins_for_team / games_for_team

    return jsonify({
        "filters": {
            "from": d_from.isoformat() if d_from else None,
            "to": d_to.isoformat() if d_to else None,
            "sport_id": sport_id,
            "team_id": team_id,
        },
        "stats": {
            "total_games": games_count,
            "finals_count": finals_count,
            "avg_points_per_final": avg_points_per_final,
            "win_rate_for_team": win_rate,
        },
        "rows": data,
    })

# Run
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
