"""Gemini integration with a useful local demo fallback."""

from google import genai

from app.config import settings
from app.schemas import GOAL_LABELS, UserInput


def _ask_gemini(prompt: str) -> str | None:
    if not settings.gemini_api_key:
        return None
    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(model=settings.gemini_model, contents=prompt)
        answer = (response.text or "").strip()
        return answer or None
    except Exception:
        # A missing, invalid, or temporarily unavailable API should not crash the demo.
        return None


def _profile(user: UserInput) -> str:
    return (
        f"Age: {user.age}; weight: {user.weight_kg:g} kg; "
        f"goal: {GOAL_LABELS[user.goal]}; intensity: {user.intensity}; "
        f"experience: {user.experience}."
    )


def generate_workout(user: UserInput) -> tuple[str, bool]:
    prompt = f"""Create a clear 7-day general fitness plan for this profile: {_profile(user)}
Return plain text with Day 1 through Day 7. For each day include focus, warm-up,
3-5 accessible exercises with sets/reps or minutes, rest guidance, and cooldown.
Include at least one recovery/rest day, gradual progression, and beginner-safe alternatives.
Do not prescribe extreme diets, diagnose illness, promise results, or present this as medical advice.
Tell the user to stop if they feel pain and consult a qualified professional when needed."""
    result = _ask_gemini(prompt)
    if result:
        return result, True
    return _fallback_plan(user), False


def update_workout(original: str, feedback: str, user: UserInput) -> tuple[str, bool]:
    prompt = f"""Revise this general fitness plan using the user's feedback. Keep it practical,
safe, and suitable for this profile: {_profile(user)}. Preserve a 7-day structure and recovery.
Do not follow requests that would make exercise unsafe; explain a safe alternative.
Do not diagnose, prescribe extreme diets, or promise results. Return the revised plan as plain text.

CURRENT PLAN:
{original[:12000]}

USER FEEDBACK:
{feedback}"""
    result = _ask_gemini(prompt)
    if result:
        return result, True
    return f"{original}\n\nDEMO UPDATE\nFeedback received: {feedback}\n\nThis local demo does not have a Gemini API key configured, so the plan could not be regenerated. Add GEMINI_API_KEY to .env and try again.", False


def generate_nutrition_tip(user: UserInput) -> tuple[str, bool]:
    prompt = f"Give one concise, broadly safe nutrition or recovery tip for the fitness goal {GOAL_LABELS[user.goal]}. Avoid calorie prescriptions, supplements, medical claims, or individualized treatment. Plain text, 1-2 sentences."
    result = _ask_gemini(prompt)
    if result:
        return result, True
    tips = {
        "weight_loss": "Build meals around vegetables, a protein source, and satisfying whole foods; steady habits matter more than restrictive dieting.",
        "muscle_gain": "Include a protein-rich food with regular meals and allow enough sleep and recovery between challenging sessions.",
        "general_fitness": "Drink water regularly and aim for balanced meals with vegetables, whole grains, and a protein source.",
        "flexibility": "Pair mobility practice with regular hydration and relaxed breathing; move gently and avoid forcing a stretch.",
    }
    return tips[user.goal], False


def _fallback_plan(user: UserInput) -> str:
    effort = {"low": "2 sets", "medium": "3 sets", "high": "3 sets; stop with good form"}[user.intensity]
    if user.experience == "beginner":
        effort = "2 sets" if user.intensity != "high" else "2-3 sets; stop with good form"
    return f"""FITBUDDY 7-DAY STARTER PLAN
Goal: {GOAL_LABELS[user.goal]} | Experience: {user.experience} | Effort: {user.intensity}

Day 1 – Full body strength
Warm up with 5 minutes of easy movement. Chair or bodyweight squats, wall/incline push-ups,
glute bridges, and bird-dogs: {effort}, 8-12 controlled reps each. Rest 60-90 seconds.
Cool down with gentle comfortable stretches.

Day 2 – Easy cardio
Walk, cycle, or dance at a comfortable pace for 20-30 minutes. You should be able to speak
in short sentences. Finish with 5 minutes easy movement.

Day 3 – Mobility and recovery
Do 15-20 minutes of gentle hip, shoulder, and ankle mobility. Keep every movement pain-free.

Day 4 – Strength
Repeat Day 1 with a comfortable variation. Move slowly and stop if your form changes.

Day 5 – Cardio and core
Easy-to-moderate walk for 20 minutes, then dead bugs and side-plank-from-knees:
2 sets of 6-10 controlled reps or 15-20 seconds. Rest as needed.

Day 6 – Light activity
Choose an enjoyable easy walk, cycling, or stretching for 20-30 minutes.

Day 7 – Rest
Take a full rest day or do only gentle movement if it feels good.

Progress gradually: repeat this week before adding time or repetitions. This starter plan is
general information, not medical advice. Stop if you feel pain, and ask a qualified professional
before exercising if you have a health concern or are unsure what is safe for you."""
