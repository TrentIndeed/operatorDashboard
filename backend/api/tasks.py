from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from db.database import get_db, Task, Goal, AISuggestion, NewsBriefing, Project
from models.schemas import (
    TaskOut, TaskCreate, TaskUpdate,
    GoalOut, GoalCreate, GoalUpdate,
    AISuggestionOut, NewsBriefingOut, CommandCenterData,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])
goals_router = APIRouter(prefix="/goals", tags=["goals"])
suggestions_router = APIRouter(prefix="/suggestions", tags=["suggestions"])
briefing_router = APIRouter(prefix="/briefing", tags=["briefing"])
command_router = APIRouter(prefix="/command-center", tags=["command-center"])


# --- Tasks ---

@router.get("/", response_model=List[TaskOut])
def get_tasks(status: str = None, db: Session = Depends(get_db)):
    q = db.query(Task)
    if status:
        q = q.filter(Task.status == status)
    return q.order_by(Task.priority_score.desc()).all()


@router.post("/", response_model=TaskOut)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    db_task = Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, update: TaskUpdate, db: Session = Depends(get_db)):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(db_task, field, value)
    db_task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_task)
    return db_task


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(db_task)
    db.commit()
    return {"ok": True}


# --- Goals ---

@goals_router.get("/", response_model=List[GoalOut])
def get_goals(timeframe: str = None, db: Session = Depends(get_db)):
    q = db.query(Goal)
    if timeframe:
        q = q.filter(Goal.timeframe == timeframe)
    return q.filter(Goal.status == "active").order_by(Goal.created_at.desc()).all()


@goals_router.post("/", response_model=GoalOut)
def create_goal(goal: GoalCreate, db: Session = Depends(get_db)):
    db_goal = Goal(**goal.model_dump())
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    return db_goal


@goals_router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: int, update: GoalUpdate, db: Session = Depends(get_db)):
    db_goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(db_goal, field, value)
    db.commit()
    db.refresh(db_goal)
    return db_goal


@goals_router.delete("/{goal_id}")
def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    db_goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(db_goal)
    db.commit()
    return {"ok": True}


# --- AI Suggestions ---

@suggestions_router.get("/", response_model=List[AISuggestionOut])
def get_suggestions(db: Session = Depends(get_db)):
    return (
        db.query(AISuggestion)
        .filter(AISuggestion.dismissed == False)
        .order_by(AISuggestion.created_at.desc())
        .limit(10)
        .all()
    )


@suggestions_router.patch("/{suggestion_id}/dismiss")
def dismiss_suggestion(suggestion_id: int, db: Session = Depends(get_db)):
    s = db.query(AISuggestion).filter(AISuggestion.id == suggestion_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    s.dismissed = True
    db.commit()
    return {"ok": True}


# --- News Briefing ---

@briefing_router.get("/", response_model=List[NewsBriefingOut])
def get_briefing(date: str = None, db: Session = Depends(get_db)):
    q = db.query(NewsBriefing).filter(NewsBriefing.dismissed == False)
    if date:
        q = q.filter(NewsBriefing.briefing_date == date)
    return q.order_by(NewsBriefing.relevance_score.desc()).limit(20).all()


@briefing_router.patch("/{item_id}/dismiss")
def dismiss_briefing_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(NewsBriefing).filter(NewsBriefing.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Briefing item not found")
    item.dismissed = True
    db.commit()
    return {"ok": True}


# --- Command Center (aggregated) ---

@command_router.get("/", response_model=CommandCenterData)
def get_command_center(db: Session = Depends(get_db)):
    from datetime import date
    today = date.today().isoformat()

    tasks = (
        db.query(Task)
        .filter(Task.status.in_(["pending", "in_progress"]))
        .order_by(Task.priority_score.desc())
        .limit(5)
        .all()
    )
    projects = db.query(Project).all()
    goals_week = db.query(Goal).filter(Goal.timeframe == "week", Goal.status == "active").all()
    goals_month = db.query(Goal).filter(Goal.timeframe == "month", Goal.status == "active").all()
    goals_quarter = db.query(Goal).filter(Goal.timeframe == "quarter", Goal.status == "active").all()
    suggestions = (
        db.query(AISuggestion)
        .filter(AISuggestion.dismissed == False)
        .order_by(AISuggestion.created_at.desc())
        .limit(5)
        .all()
    )
    briefing = (
        db.query(NewsBriefing)
        .filter(NewsBriefing.dismissed == False, NewsBriefing.briefing_date == today)
        .order_by(NewsBriefing.relevance_score.desc())
        .limit(10)
        .all()
    )

    return CommandCenterData(
        tasks=tasks,
        projects=projects,
        goals_week=goals_week,
        goals_month=goals_month,
        goals_quarter=goals_quarter,
        suggestions=suggestions,
        briefing=briefing,
    )
