import random
from datetime import date, timedelta

from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from . import models


GRADE_SUBJECTS = {
    "初一": [1, 2, 3],
    "初二": [1, 2, 3, 4],
    "初三": [1, 2, 3, 4, 5],
    "高一": [1, 2, 3, 4, 5],
    "高二": [1, 2, 3, 4, 5, 6, 7, 8, 9],
    "高三": [1, 2, 3, 4, 5, 6, 7, 8, 9],
}

SCHOOL_EXAMS = [
    ("期中考试", 70),
    ("月考一", 45),
    ("期末考试", 20),
]

QUIZ_NAMES = ["随堂小测", "周测", "单元测验"]


def _dow_date(dow: int, days_ago: int = 0) -> date:
    today = date.today()
    target = today - timedelta(days=days_ago)
    delta = (target.weekday() - dow) % 7
    return target - timedelta(days=delta)


def seed_demo_data(db: Session) -> dict:
    rng = random.Random(20260803)
    added_attendance = 0
    added_scores = 0
    added_entry_scores = 0
    skipped_attendance = 0
    skipped_scores = 0
    skipped_entry_scores = 0

    students = db.query(models.Student).all()
    courses = db.query(models.Course).options(joinedload(models.Course.students)).all()

    # 1) Attendance: last 10 weeks for every class enrollment
    for course in courses:
        if course.course_type == "self_study":
            continue
        for student in course.students:
            for week in range(10):
                att_date = _dow_date(course.day_of_week, days_ago=7 * week)
                exists = db.query(models.Attendance).filter(
                    models.Attendance.course_id == course.id,
                    models.Attendance.student_id == student.id,
                    models.Attendance.date == att_date,
                ).first()
                if exists:
                    skipped_attendance += 1
                    continue
                if rng.random() < 0.04:
                    continue
                roll = rng.random()
                if roll < 0.86: status = "present"
                elif roll < 0.93: status = "late"
                elif roll < 0.97: status = "absent"
                else: status = "leave"
                db.add(models.Attendance(
                    course_id=course.id,
                    student_id=student.id,
                    date=att_date,
                    status=status,
                    notes="",
                ))
                added_attendance += 1

    # 2) School exam records per student per grade-appropriate subject
    for student in students:
        subject_ids = GRADE_SUBJECTS.get(student.grade, [1, 2, 3])
        for subject_id in subject_ids:
            ability = rng.uniform(0.58, 0.94)
            for name, days_ago in SCHOOL_EXAMS:
                exam_date = date.today() - timedelta(days=days_ago)
                exists = db.query(models.ScoreRecord).filter(
                    models.ScoreRecord.student_id == student.id,
                    models.ScoreRecord.subject_id == subject_id,
                    models.ScoreRecord.exam_name == name,
                    models.ScoreRecord.exam_date == exam_date,
                ).first()
                if exists:
                    skipped_scores += 1
                    continue
                rate = min(1.0, max(0.35, ability + rng.uniform(-0.08, 0.08)))
                db.add(models.ScoreRecord(
                    student_id=student.id,
                    subject_id=subject_id,
                    course_id=None,
                    exam_type="school_exam",
                    exam_name=name,
                    score=round(rate * 100, 1),
                    max_score=100,
                    exam_date=exam_date,
                    notes="",
                ))
                added_scores += 1

    # 3) Quiz records per enrolled class course
    for course in courses:
        if course.course_type == "self_study":
            continue
        for student in course.students:
            ability = rng.uniform(0.55, 0.95)
            for i, name in enumerate(QUIZ_NAMES):
                exam_date = _dow_date(course.day_of_week, days_ago=42 - i * 14)
                exists = db.query(models.ScoreRecord).filter(
                    models.ScoreRecord.student_id == student.id,
                    models.ScoreRecord.course_id == course.id,
                    models.ScoreRecord.exam_name == name,
                    models.ScoreRecord.exam_date == exam_date,
                ).first()
                if exists:
                    skipped_scores += 1
                    continue
                rate = min(1.0, max(0.35, ability + rng.uniform(-0.10, 0.10)))
                db.add(models.ScoreRecord(
                    student_id=student.id,
                    subject_id=course.subject_id,
                    course_id=course.id,
                    exam_type="quiz",
                    exam_name=name,
                    score=round(rate * 100, 1),
                    max_score=100,
                    exam_date=exam_date,
                    notes="",
                ))
                added_scores += 1

    # 4) Entry diagnostic tests: one per enrolled class course, dated before quizzes
    for course in courses:
        if course.course_type == "self_study":
            continue
        for student in course.students:
            quiz_rows = db.query(models.ScoreRecord).filter(
                models.ScoreRecord.student_id == student.id,
                models.ScoreRecord.subject_id == course.subject_id,
                models.ScoreRecord.exam_type == "quiz",
            ).all()
            if not quiz_rows:
                continue
            avg_quiz = sum(r.rate for r in quiz_rows) / len(quiz_rows)
            entry_rate = min(1.0, max(0.30, avg_quiz / 100 - rng.uniform(0.06, 0.16)))
            entry_date = _dow_date(course.day_of_week, days_ago=70)
            exists = db.query(models.ScoreRecord).filter(
                models.ScoreRecord.student_id == student.id,
                models.ScoreRecord.course_id == course.id,
                models.ScoreRecord.exam_type == "entry_test",
                models.ScoreRecord.exam_name == "入班诊断测试",
                models.ScoreRecord.exam_date == entry_date,
            ).first()
            if exists:
                skipped_entry_scores += 1
                continue
            db.add(models.ScoreRecord(
                student_id=student.id,
                subject_id=course.subject_id,
                course_id=course.id,
                exam_type="entry_test",
                exam_name="入班诊断测试",
                score=round(entry_rate * 100, 1),
                max_score=100,
                exam_date=entry_date,
                notes="",
            ))
            added_entry_scores += 1

    db.commit()
    return {
        "added_attendance": added_attendance,
        "skipped_attendance": skipped_attendance,
        "added_scores": added_scores,
        "skipped_scores": skipped_scores,
        "added_entry_scores": added_entry_scores,
        "skipped_entry_scores": skipped_entry_scores,
    }
