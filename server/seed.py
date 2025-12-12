# server/seed.py
from datetime import date, time
from app import app, db
from models import Sport, Team, Venue, Game

with app.app_context():
    db.create_all()

    # --- Sports ---
    sports = ["Basketball", "Soccer", "Volleyball"]
    sport_objs = {}
    for name in sports:
        s = Sport.query.filter_by(name=name).first()
        if not s:
            s = Sport(name=name)
            db.session.add(s)
        sport_objs[name] = s

    db.session.flush()  # assign IDs

    # --- Teams (per sport) ---
    teams_by_sport = {
        "Basketball": ["Boiler Ball A", "Boiler Ball B", "Riveters"],
        "Soccer": ["Boiler FC", "West Lafayette United", "Ross–Ade Rovers"],
        "Volleyball": ["Spike Squad", "Net Ninjas", "Block Party"],
    }
    team_objs = {}
    for sport_name, team_names in teams_by_sport.items():
        sport = sport_objs[sport_name]
        for tname in team_names:
            t = Team.query.filter_by(sport_id=sport.id, name=tname).first()
            if not t:
                t = Team(sport_id=sport.id, name=tname)
                db.session.add(t)
            team_objs[(sport_name, tname)] = t

    # --- Venues ---
    venues = [
        ("CoRec Court 1", "CoRec"),
        ("CoRec Court 2", "CoRec"),
        ("Intramural Field A", "IM Fields"),
        ("Intramural Field B", "IM Fields"),
    ]
    venue_objs = {}
    for name, loc in venues:
        v = Venue.query.filter_by(name=name).first()
        if not v:
            v = Venue(name=name, location=loc)
            db.session.add(v)
        venue_objs[name] = v

    db.session.flush()

    # --- Sample Games ---
    # Today and tomorrow for easy filtering
    today = date.today()
    gdata = [
        # Basketball
        ("Basketball", "Boiler Ball A", "Boiler Ball B", "CoRec Court 1", today, time(18, 30), None, None, "scheduled"),
        ("Basketball", "Riveters", "Boiler Ball A", "CoRec Court 2", today, time(20, 0), 64, 58, "final"),
        # Soccer
        ("Soccer", "Boiler FC", "West Lafayette United", "Intramural Field A", today, time(17, 0), 2, 1, "final"),
        ("Soccer", "Ross–Ade Rovers", "Boiler FC", "Intramural Field B", today, time(19, 15), None, None, "scheduled"),
        # Volleyball
        ("Volleyball", "Spike Squad", "Net Ninjas", "CoRec Court 1", today, time(16, 0), 3, 1, "final"),
        ("Volleyball", "Block Party", "Spike Squad", "CoRec Court 2", today, time(18, 0), None, None, "scheduled"),
    ]

    for sp, home, away, venue_name, d, t, hs, as_, status in gdata:
        sport = sport_objs[sp]
        home_t = team_objs[(sp, home)]
        away_t = team_objs[(sp, away)]
        venue = venue_objs[venue_name]
        exists = Game.query.filter_by(
            sport_id=sport.id, home_team_id=home_t.id, away_team_id=away_t.id, date=d, time=t
        ).first()
        if not exists:
            db.session.add(Game(
                sport_id=sport.id,
                home_team_id=home_t.id,
                away_team_id=away_t.id,
                venue_id=venue.id,
                date=d,
                time=t,
                home_score=hs,
                away_score=as_,
                status=status
            ))

    db.session.commit()
    print("Seeded sports, teams, venues, and games.")
