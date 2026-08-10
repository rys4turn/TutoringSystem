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


STUDENT_SURNAMES = [
    "王", "李", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴",
    "徐", "孙", "马", "朱", "胡", "郭", "何", "林", "罗", "郑",
    "梁", "谢", "宋", "唐", "许", "韩", "冯", "邓", "曹", "彭",
]
STUDENT_GIVEN = [
    "子涵", "宇轩", "雨桐", "浩然", "欣怡", "梓睿", "思远", "梦琪", "嘉豪", "若溪",
    "一诺", "明轩", "诗涵", "俊杰", "雅琪", "文博", "欣妍", "天佑", "静怡", "宇航",
    "雨欣", "致远", "晨曦", "欣蕾", "泽宇", "心怡", "俊熙", "思彤", "博文", "婉婷",
]
GRADE_SEQ = ["初一", "初二", "初三", "高一", "高二", "高三"]
TEACHER_PLAN = [
    ("王老师", ["数学", "物理"]),
    ("李老师", ["数学", "英语"]),
    ("张老师", ["英语", "化学"]),
    ("刘老师", ["化学", "生物"]),
    ("陈老师", ["物理"]),
    ("杨老师", ["政治", "历史"]),
    ("赵老师", ["历史", "地理"]),
    ("黄老师", ["地理", "生物"]),
    ("周老师", ["生物", "语文"]),
    ("吴老师", ["数学"]),
    ("徐老师", ["英语"]),
    ("孙老师", ["化学"]),
    ("马老师", ["物理", "政治"]),
    ("朱老师", ["政治"]),
    ("胡老师", ["历史"]),
    ("郭老师", ["地理"]),
    ("何老师", ["生物"]),
    ("林老师", ["语文", "数学", "英语"]),
]
COURSE_SUFFIX = ["强化班", "培优班", "冲刺班", "提升班"]
STUDENT_NOTES = [
    "基础扎实，做题速度需要提升",
    "课堂互动积极",
    "需加强英语词汇积累",
    "计算准确率较高",
    "近期状态良好",
    "薄弱点为综合应用题",
    "自主学习能力较强",
    "需要定期巩固错题",
]


def reset_demo_data(db: Session) -> dict:
    db.query(models.ScheduleAdjustment).delete()
    db.query(models.Attendance).delete()
    db.query(models.ScoreRecord).delete()
    db.query(models.AiReport).delete()
    db.query(models.enrollment).delete()
    db.query(models.Course).delete()
    db.query(models.teacher_subject).delete()
    db.query(models.Teacher).delete()
    db.query(models.Student).delete()
    db.query(models.Room).delete()
    db.query(models.Subject).delete()
    db.commit()
    return generate_demo_data(db)


def generate_demo_data(db: Session) -> dict:
    rng = random.Random(20260810)
    day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    subjects = []
    for name in ["语文", "数学", "英语", "物理", "化学", "政治", "历史", "地理", "生物"]:
        subj = models.Subject(name=name)
        db.add(subj)
        subjects.append(subj)
    db.flush()
    subject_by_name = {s.name: s for s in subjects}

    rooms = []
    for name, rtype, cap, note in [
        ("1号教室", "large", 8, "大教室，容纳小班课"),
        ("2号教室", "large", 8, "大教室，容纳小班课"),
        ("3号教室", "large", 8, "大教室，容纳小班课"),
        ("4号教室", "small", 2, "小教室，一对一授课"),
        ("5号教室", "study", 15, "自习室，学生完成作业"),
    ]:
        room = models.Room(name=name, room_type=rtype, capacity=cap, notes=note)
        db.add(room)
        rooms.append(room)
    db.flush()

    teachers = []
    for tname, subj_names in TEACHER_PLAN:
        teacher = models.Teacher(name=tname, phone=f"139{rng.randint(10000000, 99999999)}", notes="")
        teacher.subjects = [subject_by_name[s] for s in subj_names]
        db.add(teacher)
        teachers.append(teacher)
    db.flush()

    students_by_grade = {g: [] for g in GRADE_SEQ}
    students = []
    name_pool = [
        f"{rng.choice(STUDENT_SURNAMES)}{rng.choice(STUDENT_GIVEN)}"
        for _ in range(600)
    ]
    for idx, grade in enumerate(GRADE_SEQ):
        grade_level = "初中" if grade.startswith("初") else "高中"
        for _ in range(26):
            while True:
                name = rng.choice(name_pool)
                if name not in students:
                    break
            at_risk = idx < 3 and rng.random() < 0.28
            student = models.Student(
                name=name,
                grade_level=grade_level,
                grade=grade,
                phone=f"138{rng.randint(10000000, 99999999)}",
                notes=rng.choice(STUDENT_NOTES),
            )
            db.add(student)
            students.append(student)
            students_by_grade[grade].append(student)
            student.attendance_tendency = rng.uniform(0.78, 0.88) if at_risk else rng.uniform(0.93, 0.99)
            student.ability = rng.uniform(0.62, 0.74) if at_risk else rng.uniform(0.72, 0.96)
    db.flush()
    all_students = students
    student_ids = {s.id for s in students}

    teacher_subject_ids = {t.id: {s.id for s in t.subjects} for t in teachers}

    def pick_teacher(subject, used):
        eligible = [t for t in teachers if subject.id in teacher_subject_ids[t.id] and t.id not in used]
        if not eligible:
            eligible = [t for t in teachers if t.id not in used]
        if not eligible:
            eligible = teachers
        chosen = rng.choice(eligible)
        used.add(chosen.id)
        return chosen

    occupied = {sid: set() for sid in student_ids}
    courses = []
    course_count = 0
    enrollment_count = 0
    slot_room_range = {
        1: (0, 2),   # 08:00-10:00 早课较少
        2: (3, 5),   # 10:00-12:00 黄金时段
        3: (3, 5),   # 13:00-15:00 黄金时段
        4: (3, 5),   # 15:00-17:00 黄金时段
        5: (0, 3),   # 18:00-20:00 晚课较少
    }

    for day in range(7):
        for slot in range(1, 6):
            low, high = slot_room_range[slot]
            room_count = rng.randint(low, high)
            if room_count == 0:
                continue
            used_teachers = set()
            chosen_rooms = rng.sample(rooms, room_count)
            for room in chosen_rooms:
                if room.room_type == "study":
                    teacher = pick_teacher(rng.choice(subjects), used_teachers)
                    name = f"综合自习·{day_names[day]}{slot}"
                    course = models.Course(
                        name=name,
                        subject_id=subjects[0].id,
                        teacher_id=teacher.id,
                        room_id=room.id,
                        day_of_week=day,
                        time_slot=slot,
                        course_type="self_study",
                        max_students=15,
                        notes="开放自习与作业辅导",
                    )
                    db.add(course)
                    db.flush()
                    pool = [s for s in all_students if (day, slot) not in occupied[s.id]]
                    count = min(rng.randint(4, 10), len(pool))
                    selected = rng.sample(pool, count)
                    course.students = selected
                    for s in selected:
                        occupied[s.id].add((day, slot))
                    courses.append(course)
                    course_count += 1
                    enrollment_count += count
                    continue

                subject = rng.choice(subjects)
                teacher = pick_teacher(subject, used_teachers)
                grade = rng.choice(GRADE_SEQ)
                if room.room_type == "small":
                    name = f"{grade}{subject.name}一对一·{day_names[day]}{slot}"
                else:
                    name = f"{grade}{subject.name}{rng.choice(COURSE_SUFFIX)}·{day_names[day]}{slot}"
                course = models.Course(
                    name=name,
                    subject_id=subject.id,
                    teacher_id=teacher.id,
                    room_id=room.id,
                    day_of_week=day,
                    time_slot=slot,
                    course_type="class",
                    max_students=2 if room.room_type == "small" else 8,
                    notes="一对一辅导" if room.room_type == "small" else "按需求排课，保留空位",
                )
                db.add(course)
                db.flush()
                pool = [s for s in students_by_grade[grade] if (day, slot) not in occupied[s.id]]
                if len(pool) < 2:
                    pool = [s for s in all_students if (day, slot) not in occupied[s.id]]
                if room.room_type == "small":
                    count = min(1, len(pool))
                else:
                    count = min(rng.randint(2, 7), len(pool))
                if count == 0:
                    continue
                selected = rng.sample(pool, count)
                course.students = selected
                for s in selected:
                    occupied[s.id].add((day, slot))
                courses.append(course)
                course_count += 1
                enrollment_count += count

    attendance_rows = []
    score_rows = []
    for course in courses:
        for student in course.students:
            tendency = getattr(student, "attendance_tendency", 0.95)
            for week in range(10):
                att_date = _dow_date(course.day_of_week, days_ago=7 * week)
                roll = rng.random()
                if roll < 0.02:
                    continue
                absent_p = max(0.01, 1 - tendency)
                late_p = min(0.14, absent_p + 0.06)
                leave_p = min(0.18, late_p + 0.02)
                if roll < absent_p:
                    status = "absent"
                elif roll < late_p:
                    status = "late"
                elif roll < leave_p:
                    status = "leave"
                else:
                    status = "present"
                attendance_rows.append(models.Attendance(
                    course_id=course.id,
                    student_id=student.id,
                    date=att_date,
                    status=status,
                    notes="",
                ))

    student_subject_ids = {}
    for course in courses:
        for student in course.students:
            student_subject_ids.setdefault(student.id, set()).add(course.subject_id)

    for student in students:
        ability = getattr(student, "ability", 0.8)
        for subject_id in student_subject_ids.get(student.id, set()):
            for name, days_ago in [("期中考试", 70), ("月考一", 45), ("期末考试", 20)]:
                rate = min(1.0, max(0.35, ability + rng.uniform(-0.09, 0.08)))
                score_rows.append(models.ScoreRecord(
                    student_id=student.id,
                    subject_id=subject_id,
                    course_id=None,
                    exam_type="school_exam",
                    exam_name=name,
                    score=round(rate * 100, 1),
                    max_score=100,
                    exam_date=date.today() - timedelta(days=days_ago),
                    notes="",
                ))

    for course in courses:
        for student in course.students:
            ability = getattr(student, "ability", 0.8)
            quiz_rates = []
            for i, name in enumerate(["周测一", "周测二", "周测三"]):
                quiz_date = _dow_date(course.day_of_week, days_ago=42 - i * 14)
                rate = min(1.0, max(0.35, ability + rng.uniform(-0.10, 0.10)))
                quiz_rates.append(rate)
                score_rows.append(models.ScoreRecord(
                    student_id=student.id,
                    subject_id=course.subject_id,
                    course_id=course.id,
                    exam_type="quiz",
                    exam_name=name,
                    score=round(rate * 100, 1),
                    max_score=100,
                    exam_date=quiz_date,
                    notes="",
                ))
            if quiz_rates:
                entry_rate = min(1.0, max(0.3, sum(quiz_rates) / len(quiz_rates) - rng.uniform(0.05, 0.14)))
                score_rows.append(models.ScoreRecord(
                    student_id=student.id,
                    subject_id=course.subject_id,
                    course_id=course.id,
                    exam_type="entry_test",
                    exam_name="入班诊断测试",
                    score=round(entry_rate * 100, 1),
                    max_score=100,
                    exam_date=_dow_date(course.day_of_week, days_ago=70),
                    notes="",
                ))

    adjustments = []
    for _ in range(16):
        course = rng.choice(courses)
        if rng.random() < 0.3:
            adjustments.append(models.ScheduleAdjustment(
                course_id=course.id,
                adjustment_date=date.today() - timedelta(days=rng.randint(1, 30)),
                original_day=course.day_of_week,
                original_slot=course.time_slot,
                original_room_id=course.room_id,
                new_day=None,
                new_slot=None,
                new_room_id=None,
                adjustment_type="cancelled",
                reason=rng.choice(["教师临时请假", "学生集中考试", "教室临时维修"]),
            ))
        else:
            new_day = rng.randint(0, 6)
            new_slot = rng.randint(1, 5)
            if new_day == course.day_of_week and new_slot == course.time_slot:
                new_day = (new_day + rng.choice([1, -1])) % 7
            new_room = rng.choice(rooms).id
            adjustments.append(models.ScheduleAdjustment(
                course_id=course.id,
                adjustment_date=date.today() - timedelta(days=rng.randint(1, 30)),
                original_day=course.day_of_week,
                original_slot=course.time_slot,
                original_room_id=course.room_id,
                new_day=new_day,
                new_slot=new_slot,
                new_room_id=new_room,
                adjustment_type="rescheduled",
                reason=rng.choice(["教师调课", "教室档期调整", "学生课后活动冲突"]),
            ))

    db.add_all(attendance_rows)
    db.add_all(score_rows)
    db.add_all(adjustments)
    db.commit()

    return {
        "students": len(students),
        "teachers": len(teachers),
        "courses": course_count,
        "enrollments": enrollment_count,
        "rooms": len(rooms),
        "subjects": len(subjects),
        "attendance": len(attendance_rows),
        "scores": len(score_rows),
        "adjustments": len(adjustments),
    }
