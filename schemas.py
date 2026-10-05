"""Validated form data and allowed choices."""

from typing import Literal

from pydantic import BaseModel, Field

Goal = Literal["weight_loss", "muscle_gain", "general_fitness", "flexibility"]
Intensity = Literal["low", "medium", "high"]
Experience = Literal["beginner", "intermediate", "advanced"]


class UserInput(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    age: int = Field(ge=16, le=90)
    weight_kg: float = Field(gt=25, le=300)
    goal: Goal
    intensity: Intensity
    experience: Experience = "beginner"


GOAL_LABELS = {
    "weight_loss": "Weight loss",
    "muscle_gain": "Muscle gain",
    "general_fitness": "General fitness",
    "flexibility": "Flexibility",
}
