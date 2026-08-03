from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import date
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/scores", tags=["scores"])

@router.get("/", response_model=list[schemas.ScoreRecordOut])
def list_scores(
    student_id: int = None,
    subject_id: int = None,
    course_id: int = None,
    exam_type: str = None,
    date_from: date = None,
    date_to: date = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.ScoreRecord).options(
        joinedload(models.ScoreRecord.student),
        joinedload(models.ScoreRecord.subject),
        joinedload(models.ScoreRecord.course),
    )
    if student_id: q = q.filter(models.ScoreRecord.student_id == student_id)
    if subject_id: q = q.filter(models.ScoreRecord.subject_id == subject_id)
    if course_id: q = q.filter(models.ScoreRecord.course_id == course_id)
    if exam_type: q = q.filter(models.ScoreRecord.exam_type == exam_type)
    if date_from: q = q.filter(models.ScoreRecord.exam_date >= date_from)
    if date_to: q = q.filter(models.ScoreRecord.exam_date <= date_to)
    return q.order_by(models.ScoreRecord.exam_date.desc(), models.ScoreRecord.id.desc()).all()

@router.post("/", response_model=schemas.ScoreRecordOut)
def create_score(body: schemas.ScoreRecordCreate, db: Session = Depends(get_db)):
    if body.exam_type not in schemas.EXAM_TYPES:
        raise HTTPException(status_code=400, detail="exam_type must be school_exam or quiz")
    if not db.query(models.Student).filter(models.Student.id == body.student_id).first():
        raise HTTPException(status_code=404, detail="Student not found")
    if not db.query(models.Subject).filter(models.Subject.id == body.subject_id).first():
        raise HTTPException(status_code=404, detail="Subject not found")
    if body.course_id and not db.query(models.Course).filter(models.Course.id == body.course_id).first():
        raise HTTPException(status_code=404, detail="Course not found")
    rec = models.ScoreRecord(**body.model_dump())
    db.add(rec); db.commit(); db.refresh(rec)
    return _load_score(db, rec.id)

@router.put("/{score_id}", response_model=schemas.ScoreRecordOut)
def update_score(score_id: int, body: schemas.ScoreRecordUpdate, db: Session = Depends(get_db)):
    rec = db.query(models.ScoreRecord).filter(models.ScoreRecord.id == score_id).first()
    if not rec: raise HTTPException(status_code=404, detail="Score record not found")
    upd = body.model_dump(exclude_unset=True)
    if upd.get("exam_type") and upd["exam_type"] not in schemas.EXAM_TYPES:
        raise HTTPException(status_code=400, detail="exam_type must be school_exam or quiz")
    for key, value in upd.items(): setattr(rec, key, value)
    db.commit()
    return _load_score(db, score_id)

@router.delete("/{score_id}")
def delete_score(score_id: int, db: Session = Depends(get_db)):
    rec = db.query(models.ScoreRecord).filter(models.ScoreRecord.id == score_id).first()
    if not rec: raise HTTPException(status_code=404, detail="Score record not found")
    db.delete(rec); db.commit()
    return {"ok": True}

def _load_score(db: Session, score_id: int):
    return db.query(models.ScoreRecord).options(
        joinedload(models.ScoreRecord.student),
        joinedload(models.ScoreRecord.subject),
        joinedload(models.ScoreRecord.course),
    ).filter(models.ScoreRecord.id == score_id).first()
