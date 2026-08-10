from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..demo_data import seed_demo_data, reset_demo_data

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/status")
def demo_status(db: Session = Depends(get_db)):
    return {
        "students": db.query(models.Student).count(),
        "courses": db.query(models.Course).count(),
        "attendance": db.query(models.Attendance).count(),
        "scores": db.query(models.ScoreRecord).count(),
    }


@router.post("/seed")
def seed_demo(db: Session = Depends(get_db)):
    return seed_demo_data(db)


@router.post("/reset")
def reset_demo(db: Session = Depends(get_db)):
    return reset_demo_data(db)
