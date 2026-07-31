from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import date
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/attendance", tags=["attendance"])

@router.get("/")
def list_attendance(course_id: int = None, date_val: date = None, db: Session = Depends(get_db)) -> list[schemas.AttendanceOut]:
    q = db.query(models.Attendance).options(joinedload(models.Attendance.student), joinedload(models.Attendance.course))
    if course_id: q = q.filter(models.Attendance.course_id == course_id)
    if date_val: q = q.filter(models.Attendance.date == date_val)
    return q.all()

@router.post("/batch")
def batch_attendance(body: schemas.AttendanceBatch, db: Session = Depends(get_db)):
    course = db.query(models.Course).filter(models.Course.id == body.course_id).first()
    if not course: raise HTTPException(status_code=404, detail="Course not found")
    for rec in body.records:
        sid, status, notes = rec.get("student_id"), rec.get("status", "present"), rec.get("notes", "")
        existing = db.query(models.Attendance).filter(models.Attendance.course_id == body.course_id, models.Attendance.student_id == sid, models.Attendance.date == body.date_val).first()
        if existing:
            existing.status = status; existing.notes = notes
        else:
            db.add(models.Attendance(course_id=body.course_id, student_id=sid, date=body.date_val, status=status, notes=notes))
    db.commit()
    return {"ok": True}

@router.get("/report")
def attendance_report(student_id: int = None, date_from: date = None, date_to: date = None, db: Session = Depends(get_db)) -> list[schemas.AttendanceReportItem]:
    q = db.query(models.Attendance).options(joinedload(models.Attendance.student), joinedload(models.Attendance.course).joinedload(models.Course.subject))
    if student_id: q = q.filter(models.Attendance.student_id == student_id)
    if date_from: q = q.filter(models.Attendance.date >= date_from)
    if date_to: q = q.filter(models.Attendance.date <= date_to)
    attendances = q.order_by(models.Attendance.date.desc()).all()
    result = {}
    for a in attendances:
        sid = a.student_id
        if sid not in result:
            result[sid] = schemas.AttendanceReportItem(student=a.student)
        a_out = schemas.AttendanceOut.model_validate(a)
        result[sid].records.append(a_out)
        if a.status == "present": result[sid].present_count += 1
        else: result[sid].absent_count += 1
    return list(result.values())
