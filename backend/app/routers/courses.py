from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/courses", tags=["courses"])

@router.get("/", response_model=list[schemas.CourseOut])
def list_courses(day_of_week: int = Query(None), db: Session = Depends(get_db)):
    q = db.query(models.Course).options(joinedload(models.Course.subject), joinedload(models.Course.teacher).joinedload(models.Teacher.subjects), joinedload(models.Course.room), joinedload(models.Course.students))
    if day_of_week is not None: q = q.filter(models.Course.day_of_week == day_of_week)
    courses = q.all()
    for c in courses: c.student_count = len(c.students)
    return courses

@router.post("/", response_model=schemas.CourseOut)
def create_course(course: schemas.CourseCreate, db: Session = Depends(get_db)):
    conflict = db.query(models.Course).filter(models.Course.room_id == course.room_id, models.Course.day_of_week == course.day_of_week, models.Course.time_slot == course.time_slot).first()
    if conflict: raise HTTPException(status_code=400, detail="Time slot conflict for this room")
    db_course = models.Course(name=course.name, subject_id=course.subject_id, teacher_id=course.teacher_id, room_id=course.room_id, day_of_week=course.day_of_week, time_slot=course.time_slot, course_type=course.course_type, max_students=course.max_students, notes=course.notes)
    if course.student_ids: db_course.students = db.query(models.Student).filter(models.Student.id.in_(course.student_ids)).all()
    db.add(db_course); db.commit(); db.refresh(db_course)
    return _load_course(db, db_course.id)

@router.put("/{course_id}", response_model=schemas.CourseOut)
def update_course(course_id: int, course: schemas.CourseUpdate, db: Session = Depends(get_db)):
    db_course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not db_course: raise HTTPException(status_code=404, detail="Course not found")
    upd = course.model_dump(exclude_unset=True)
    student_ids = upd.pop("student_ids", None)
    new_room = upd.get("room_id", db_course.room_id); new_dow = upd.get("day_of_week", db_course.day_of_week); new_slot = upd.get("time_slot", db_course.time_slot)
    if new_room != db_course.room_id or new_dow != db_course.day_of_week or new_slot != db_course.time_slot:
        conflict = db.query(models.Course).filter(models.Course.room_id == new_room, models.Course.day_of_week == new_dow, models.Course.time_slot == new_slot, models.Course.id != course_id).first()
        if conflict: raise HTTPException(status_code=400, detail="Time slot conflict for this room")
    for key, value in upd.items(): setattr(db_course, key, value)
    if student_ids is not None: db_course.students = db.query(models.Student).filter(models.Student.id.in_(student_ids)).all()
    db.commit()
    return _load_course(db, course_id)

@router.delete("/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db)):
    db_course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not db_course: raise HTTPException(status_code=404, detail="Course not found")
    db.delete(db_course); db.commit()
    return {"ok": True}

def _load_course(db: Session, course_id: int):
    c = db.query(models.Course).options(joinedload(models.Course.subject), joinedload(models.Course.teacher).joinedload(models.Teacher.subjects), joinedload(models.Course.room), joinedload(models.Course.students)).filter(models.Course.id == course_id).first()
    c.student_count = len(c.students)
    return c
