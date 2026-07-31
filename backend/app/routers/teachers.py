from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/teachers", tags=["teachers"])

@router.get("/", response_model=list[schemas.TeacherOut])
def list_teachers(db: Session = Depends(get_db)):
    return db.query(models.Teacher).options(joinedload(models.Teacher.subjects)).all()

@router.post("/", response_model=schemas.TeacherOut)
def create_teacher(teacher: schemas.TeacherCreate, db: Session = Depends(get_db)):
    db_teacher = models.Teacher(name=teacher.name, phone=teacher.phone, notes=teacher.notes)
    if teacher.subject_ids:
        db_teacher.subjects = db.query(models.Subject).filter(models.Subject.id.in_(teacher.subject_ids)).all()
    db.add(db_teacher); db.commit(); db.refresh(db_teacher)
    return db.query(models.Teacher).options(joinedload(models.Teacher.subjects)).filter(models.Teacher.id == db_teacher.id).first()

@router.put("/{teacher_id}", response_model=schemas.TeacherOut)
def update_teacher(teacher_id: int, teacher: schemas.TeacherCreate, db: Session = Depends(get_db)):
    db_teacher = db.query(models.Teacher).filter(models.Teacher.id == teacher_id).first()
    if not db_teacher: raise HTTPException(status_code=404, detail="Teacher not found")
    db_teacher.name = teacher.name; db_teacher.phone = teacher.phone; db_teacher.notes = teacher.notes
    if teacher.subject_ids is not None:
        db_teacher.subjects = db.query(models.Subject).filter(models.Subject.id.in_(teacher.subject_ids)).all()
    db.commit(); db.refresh(db_teacher)
    return db.query(models.Teacher).options(joinedload(models.Teacher.subjects)).filter(models.Teacher.id == db_teacher.id).first()

@router.delete("/{teacher_id}")
def delete_teacher(teacher_id: int, db: Session = Depends(get_db)):
    db_teacher = db.query(models.Teacher).filter(models.Teacher.id == teacher_id).first()
    if not db_teacher: raise HTTPException(status_code=404, detail="Teacher not found")
    db.delete(db_teacher); db.commit()
    return {"ok": True}
