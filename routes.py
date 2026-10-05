"""Web routes for the user pages, feedback flow, and protected coach dashboard."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import PROJECT_ROOT, settings
from app.database import get_db
from app.models import Feedback, User, WorkoutPlan
from app.schemas import GOAL_LABELS, Experience, Goal, Intensity, UserInput
from app.services.ai import generate_nutrition_tip, generate_workout, update_workout

router = APIRouter()
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "app" / "templates"))
security = HTTPBasic()


def _form_values(name="", age="", weight_kg="", goal="general_fitness", intensity="medium", experience="beginner"):
    return {"name": name, "age": age, "weight_kg": weight_kg, "goal": goal,
            "intensity": intensity, "experience": experience}


def _render_result(request: Request, user: User, plan: WorkoutPlan, *, updated=False, ai_used=False, message=None):
    return templates.TemplateResponse(request=request, name="result.html", context={
        "user": user, "plan": plan, "workout_text": plan.updated_plan if updated and plan.updated_plan else plan.original_plan,
        "updated": updated, "ai_used": ai_used, "message": message,
        "goal_labels": GOAL_LABELS,
    })


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"form": _form_values(), "error": None})


@router.post("/generate-workout", response_class=HTMLResponse)
def create_workout(
    request: Request,
    name: Annotated[str, Form()],
    age: Annotated[int, Form()],
    weight_kg: Annotated[float, Form()],
    goal: Annotated[Goal, Form()],
    intensity: Annotated[Intensity, Form()],
    experience: Annotated[Experience, Form()] = "beginner",
    db: Session = Depends(get_db),
):
    try:
        data = UserInput(name=name.strip(), age=age, weight_kg=weight_kg, goal=goal, intensity=intensity, experience=experience)
    except Exception as exc:
        return templates.TemplateResponse(request=request, name="index.html", status_code=422,
            context={"form": _form_values(name, age, weight_kg, goal, intensity, experience), "error": str(exc)})

    user = User(name=data.name, age=data.age, weight_kg=data.weight_kg, goal=data.goal,
                intensity=data.intensity, experience=data.experience)
    workout, workout_ai = generate_workout(data)
    tip, tip_ai = generate_nutrition_tip(data)
    plan = WorkoutPlan(original_plan=workout, nutrition_tip=tip)
    user.plans.append(plan)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.refresh(plan)
    return _render_result(request, user, plan, ai_used=workout_ai or tip_ai)


@router.post("/submit-feedback/{plan_id}", response_class=HTMLResponse)
def submit_feedback(
    request: Request,
    plan_id: int,
    feedback: Annotated[str, Form(min_length=4, max_length=1000)],
    db: Session = Depends(get_db),
):
    plan = db.scalar(select(WorkoutPlan).options(selectinload(WorkoutPlan.user)).where(WorkoutPlan.id == plan_id))
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    current_plan = plan.updated_plan or plan.original_plan
    data = UserInput(name=plan.user.name, age=plan.user.age, weight_kg=plan.user.weight_kg,
                     goal=plan.user.goal, intensity=plan.user.intensity, experience=plan.user.experience)
    revised, ai_used = update_workout(current_plan, feedback.strip(), data)
    plan.updated_plan = revised
    plan.updated_at = datetime.utcnow()
    plan.feedback_entries.append(Feedback(message=feedback.strip()))
    db.commit()
    return _render_result(request, plan.user, plan, updated=True, ai_used=ai_used,
                           message="Your feedback has been saved and the plan has been updated.")


def _require_admin(credentials: Annotated[HTTPBasicCredentials, Depends(security)]) -> str:
    if not settings.admin_enabled:
        raise HTTPException(status_code=503, detail="Admin dashboard is not configured. Set ADMIN_USERNAME and ADMIN_PASSWORD in .env.")
    import secrets
    user_ok = secrets.compare_digest(credentials.username.encode(), settings.admin_username.encode())
    pass_ok = secrets.compare_digest(credentials.password.encode(), settings.admin_password.encode())
    if not (user_ok and pass_ok):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials",
                            headers={"WWW-Authenticate": "Basic"})
    return credentials.username


@router.get("/view-all-users", response_class=HTMLResponse)
def view_all_users(request: Request, _: str = Depends(_require_admin), db: Session = Depends(get_db)):
    users = db.scalars(select(User).options(selectinload(User.plans).selectinload(WorkoutPlan.feedback_entries)).order_by(User.created_at.desc())).all()
    return templates.TemplateResponse(request=request, name="all_users.html", context={"users": users, "goal_labels": GOAL_LABELS})
