import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    phone_number = Column(String, unique=True, nullable=False, index=True)
    name = Column(String)
    age = Column(Integer)
    weight_kg = Column(Float)
    height_cm = Column(Float)
    fitness_level = Column(String)  # beginner | intermediate | advanced
    goals = Column(JSON)            # list[str]
    equipment = Column(JSON)        # list[str] — current available equipment
    default_equipment = Column(JSON)  # list[str] — home gym / permanent equipment
    equipment_context_note = Column(String)       # e.g. "camping trip", "hotel gym"
    equipment_context_expires_at = Column(DateTime)  # restore default after this
    preferred_days = Column(JSON)   # list[str]
    timezone = Column(String, default="UTC")
    memory_summary = Column(Text)   # rolling AI-generated summary of conversation history
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workout_logs = relationship("WorkoutLog", back_populates="user")
    workout_plans = relationship("WorkoutPlan", back_populates="user")
    nutrition_logs = relationship("NutritionLog", back_populates="user")
    conversation_messages = relationship("ConversationMessage", back_populates="user")


class WorkoutPlan(Base):
    __tablename__ = "workout_plans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String)
    duration_weeks = Column(Integer)
    days_per_week = Column(Integer)
    # {week_1: {monday: [{exercise, sets, reps, rest_seconds}]}}
    plan_data = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="workout_plans")


class WorkoutLog(Base):
    __tablename__ = "workout_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    logged_at = Column(DateTime, default=datetime.utcnow)
    # [{name, sets: [{reps, weight_kg}], notes}]
    exercises = Column(JSON)
    duration_minutes = Column(Integer)
    notes = Column(Text)

    user = relationship("User", back_populates="workout_logs")


class PersonalRecord(Base):
    __tablename__ = "personal_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    exercise_name = Column(String, nullable=False)
    weight_kg = Column(Float)
    reps = Column(Integer)
    achieved_at = Column(DateTime, default=datetime.utcnow)


class NutritionLog(Base):
    __tablename__ = "nutrition_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    logged_at = Column(DateTime, default=datetime.utcnow)
    meal_name = Column(String)
    calories = Column(Float)
    protein_g = Column(Float)
    carbs_g = Column(Float)
    fat_g = Column(Float)
    notes = Column(Text)

    user = relationship("User", back_populates="nutrition_logs")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)   # user | assistant
    content = Column(Text, nullable=False)
    channel = Column(String)               # whatsapp | voice_call | web | app
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="conversation_messages")


class ExerciseCache(Base):
    """Cached ExerciseDB API results — avoids repeated API calls for the same exercise."""
    __tablename__ = "exercise_cache"

    id = Column(String, primary_key=True)           # ExerciseDB exercise ID
    name = Column(String, nullable=False, index=True)
    name_normalized = Column(String, index=True)    # lowercase, stripped for fuzzy search
    gif_url = Column(String)
    target_muscle = Column(String)
    body_part = Column(String)
    equipment = Column(String)
    instructions = Column(JSON)                     # list[str]
    cached_at = Column(DateTime, default=datetime.utcnow)
