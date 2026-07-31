from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/subjects", tags=["subjects"])

@router.get("/", response_model=list[schemas.SubjectOut])
def list_subjects(db: Session = Depends(get_db)):
    return db.query(models.Subject).all()

@router.post("/", response_model=schemas.SubjectOut)
def create_subject(subject: schemas.SubjectCreate, db: Session = Depends(get_db)):
    if db.query(models.Subject).filter(models.Subject.name == subject.name).first():
        raise HTTPException(status_code=400, detail="Subject already exists")
    db_subject = models.Subject(**subject.model_dump())
    db.add(db_subject); db.commit(); db.refresh(db_subject)
    return db_subject
