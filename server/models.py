# server/models.py
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, CheckConstraint, Index

db = SQLAlchemy()

# Tables

class Sport(db.Model):
    __tablename__ = "sport"
    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)  # e.g., Basketball

    teams = db.relationship("Team", back_populates="sport", cascade="all, delete")
    games = db.relationship("Game", back_populates="sport", cascade="all, delete")

    def __repr__(self):
        return f"<Sport id={self.id} name={self.name!r}>"

class Team(db.Model):
    __tablename__ = "team"
    id       = db.Column(db.Integer, primary_key=True)
    sport_id = db.Column(db.Integer, db.ForeignKey("sport.id"), nullable=False, index=True)
    name     = db.Column(db.String(120), nullable=False)  # e.g., Boiler Ball A

    sport = db.relationship("Sport", back_populates="teams")
    home_games = db.relationship("Game", foreign_keys="Game.home_team_id", back_populates="home_team", cascade="all, delete")
    away_games = db.relationship("Game", foreign_keys="Game.away_team_id", back_populates="away_team", cascade="all, delete")

    __table_args__ = (
        UniqueConstraint("sport_id", "name", name="uq_team_sport_name"),
    )

    def __repr__(self):
        return f"<Team id={self.id} name={self.name!r} sport_id={self.sport_id}>"

class Venue(db.Model):
    __tablename__ = "venue"
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(120), nullable=False, unique=True)
    location = db.Column(db.String(120), nullable=True)

    games = db.relationship("Game", back_populates="venue", cascade="all, delete")

    def __repr__(self):
        return f"<Venue id={self.id} name={self.name!r}>"

class Game(db.Model):
    __tablename__ = "game"
    id = db.Column(db.Integer, primary_key=True)

    sport_id     = db.Column(db.Integer, db.ForeignKey("sport.id"), nullable=False, index=True)
    home_team_id = db.Column(db.Integer, db.ForeignKey("team.id"),  nullable=False, index=True)
    away_team_id = db.Column(db.Integer, db.ForeignKey("team.id"),  nullable=False, index=True)
    venue_id     = db.Column(db.Integer, db.ForeignKey("venue.id"), nullable=True,  index=True)

    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)

    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)

    status      = db.Column(db.String(16), nullable=False, default="scheduled")
    created_at  = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    row_version = db.Column(db.Integer, nullable=False, default=0)

    # Relationships
    sport     = db.relationship("Sport", back_populates="games")
    home_team = db.relationship("Team", foreign_keys=[home_team_id], back_populates="home_games")
    away_team = db.relationship("Team", foreign_keys=[away_team_id], back_populates="away_games")
    venue     = db.relationship("Venue", back_populates="games")

    __table_args__ = (
        CheckConstraint("status IN ('scheduled','final')", name="ck_game_status"),
        CheckConstraint("home_team_id <> away_team_id",   name="ck_game_distinct_teams"),
    )

    def __repr__(self):
        return f"<Game id={self.id} sport_id={self.sport_id} date={self.date} time={self.time} v={self.row_version}>"

# Indexes
Index("ix_game_sport_date", Game.sport_id, Game.date)
Index("ix_game_home_date",  Game.home_team_id, Game.date)
Index("ix_game_away_date",  Game.away_team_id, Game.date)
Index("ix_team_sport", Team.sport_id)
