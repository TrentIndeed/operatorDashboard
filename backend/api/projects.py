from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from db.database import get_db, Project
from models.schemas import ProjectOut, ProjectCreate, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=List[ProjectOut])
def get_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.id).all()


@router.post("/", response_model=ProjectOut)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    db_project = Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, update: ProjectUpdate, db: Session = Depends(get_db)):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(db_project, field, value)
    db.commit()
    db.refresh(db_project)
    return db_project
