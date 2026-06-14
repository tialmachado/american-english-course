"""SQLite + SQLAlchemy models for tracking progress."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "study.db"
DB_PATH.parent.mkdir(exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", future=True, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


class Progress(Base):
    """One row per resource the user has interacted with."""
    __tablename__ = "progress"
    id = Column(Integer, primary_key=True)
    resource_id = Column(String, unique=True, index=True, nullable=False)
    completed = Column(Integer, default=0)         # 0/1
    favorite = Column(Integer, default=0)          # 0/1
    last_position = Column(Float, default=0.0)     # seconds for media
    duration = Column(Float, default=0.0)          # seconds
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True)
    resource_id = Column(String, unique=True, index=True, nullable=False)
    body = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Session_(Base):
    """A study session: tracks streaks and minutes."""
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True)
    day = Column(String, index=True, nullable=False)   # YYYY-MM-DD (local)
    seconds_listening = Column(Integer, default=0)
    seconds_other = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("day", name="uq_session_day"),)


class StudySession(Base):
    """A wall-clock study session: starts on check-in, ends on pause/stop."""
    __tablename__ = "study_sessions"
    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)         # null = still running
    seconds = Column(Integer, default=0)               # filled on stop
    day = Column(String, index=True, nullable=True)    # YYYY-MM-DD (local of started_at)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return SessionLocal()
