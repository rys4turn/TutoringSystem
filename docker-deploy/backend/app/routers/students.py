from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/students", tags=["students"])

@router.get("/", response_model=list[schemas.StudentOut])
def list_students(db: Session = Depends(get_db)):
    return db.query(models.Student).all()

@router.post("/", response_model=schemas.StudentOut)
def create_student(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    db_student = models.Student(**student.model_dump())
    db.add(db_student); db.commit(); db.refresh(db_student)
    return db_student

@router.put("/{student_id}", response_model=schemas.StudentOut)
def update_student(student_id: int, student: schemas.StudentCreate, db: Session = Depends(get_db)):
    db_student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not db_student: raise HTTPException(status_code=404, detail="Student not found")
    for key, value in student.model_dump().items(): setattr(db_student, key, value)
    db.commit(); db.refresh(db_student)
    return db_student

@router.delete("/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    db_student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not db_student: raise HTTPException(status_code=404, detail="Student not found")
    db.delete(db_student); db.commit()
    return {"ok": True}
