# -*- coding: utf-8 -*-
"""
演示数据生成器。

规则（贴合真实教学场景）：
1. 每个学生在校所有应考科目都有学校考试成绩（不限于补习科目），用于完整学情分析；
2. 高中分文理：高二/高三只记录本方向科目（文科：语数英+政史地；理科：语数英+物化生），
   高一记录全科；初中按年级递增记录学校科目；
3. 补习效果模拟：出勤好、坚持上课的学生，学校考试与课后测验成绩呈缓慢上升；
   出勤差、不好好上课的学生成绩平稳甚至下滑；未补习科目仅有自然波动；
4. 入班诊断 → 课后测验逐次上升，与学校考试成绩趋势互相印证。
"""
import random
from datetime import date, timedelta

from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from . import models


# 科目 id：1语文 2数学 3英语 4物理 5化学 6政治 7历史 8地理 9生物
ALL_SUBJECT_IDS = list(range(1, 10))

# 初中各年级在校考试科目（含会考科目）
GRADE_SUBJECTS = {
    "初一": [1, 2, 3, 6, 7, 8, 9],
    "初二": [1, 2, 3, 4, 6, 7, 8, 9],
    "初三": [1, 2, 3, 4, 5, 6, 7, 8, 9],
    "高一": [1, 2, 3, 4, 5, 6, 7, 8, 9],
}

TRACK_SUBJECTS = {
    "文科": {6, 7, 8},   # 政治 历史 地理
    "理科": {4, 5, 9},   # 物理 化学 生物
}

# 学校考试时间线：由远及近，用于模拟补习带来的缓慢提升
SCHOOL_EXAMS = [
    ("开学摸底考", 110),
    ("月考一", 80),
    ("期中考试", 50),
    ("月考二", 30),
    ("期末考试", 10),
]

QUIZ_NAMES = ["入班诊断测试", "周测一", "周测二", "周测三"]
QUIZ_DAYS_AGO = [70, 42, 28, 14]


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _dow_date(dow: int, days_ago: int = 0) -> date:
    today = date.today()
    target = today - timedelta(days=days_ago)
    delta = (target.weekday() - dow) % 7
    return target - timedelta(days=delta)


def grade_subject_ids(student) -> list[int]:
    """学生在校考试科目集合（与文理分科相关）。"""
    grade = student.grade
    if grade in GRADE_SUBJECTS:
        return GRADE_SUBJECTS[grade]
    if grade in ("高二", "高三"):
        track = getattr(student, "track", "") or ""
        extra = TRACK_SUBJECTS.get(track, TRACK_SUBJECTS["理科"])
        return [1, 2, 3] + sorted(extra)
    return [1, 2, 3]


def build_student_profiles(db: Session, rng: random.Random) -> dict:
    """为每个学生在每个应考科目生成基础能力、是否补习、补习质量档案。"""
    students = db.query(models.Student).all()
    enrollments = db.query(models.enrollment).all()
    student_course_subjects = {}
    for sid, cid in enrollments:
        student_course_subjects.setdefault(sid, set()).add(cid)
    course_subject = {}
    for c in db.query(models.Course).all():
        course_subject[c.id] = c.subject_id

    profiles = {}
    for student in students:
        ability = getattr(student, "ability", rng.uniform(0.5, 0.9))
        tendency = getattr(student, "attendance_tendency", 0.9)
        tutored = {
            course_subject[cid]
            for cid in student_course_subjects.get(student.id, set())
            if cid in course_subject
        }
        subj = {}
        for subject_id in grade_subject_ids(student):
            base = _clamp(ability + rng.uniform(-0.08, 0.08), 0.30, 0.97)
            subj[subject_id] = {
                "base": base,
                "tutored": subject_id in tutored,
                "tendency": tendency,
            }
        profiles[student.id] = subj
    return profiles


def school_exam_rate(profile: dict, index: int, rng: random.Random) -> float:
    """按考试序号模拟得分率：补习且出勤好 → 缓慢提升；出勤差 → 不提升。"""
    progress = index / max(1, len(SCHOOL_EXAMS) - 1)
    tutored = profile["tutored"]
    tendency = profile["tendency"]
    if tutored:
        if tendency >= 0.93:
            gain = progress * rng.uniform(0.12, 0.22)
        elif tendency >= 0.85:
            gain = progress * rng.uniform(0.06, 0.12)
        elif tendency >= 0.75:
            gain = progress * rng.uniform(0.00, 0.06)
        else:
            gain = progress * rng.uniform(-0.07, 0.01)
    else:
        gain = progress * rng.uniform(-0.02, 0.04)
    noise = rng.uniform(-0.04, 0.04)
    return _clamp(profile["base"] + gain + noise, 0.22, 0.985)


def quiz_exam_rate(profile: dict, index: int, rng: random.Random) -> float:
    """课后测验：入班诊断(index=0) → 周测逐次，出勤好的补习科目稳步上升。"""
    progress = index / max(1, len(QUIZ_NAMES) - 1)
    tutored = profile["tutored"]
    tendency = profile["tendency"]
    if tutored:
        if tendency >= 0.93:
            gain = progress * rng.uniform(0.08, 0.15)
        elif tendency >= 0.85:
            gain = progress * rng.uniform(0.03, 0.08)
        elif tendency >= 0.75:
            gain = progress * rng.uniform(-0.01, 0.04)
        else:
            gain = progress * rng.uniform(-0.08, -0.01)
    else:
        gain = progress * rng.uniform(-0.02, 0.03)
    noise = rng.uniform(-0.05, 0.05)
    return _clamp(profile["base"] + gain + noise, 0.20, 0.985)


def seed_demo_data(db: Session) -> dict:
    """增量生成：为已有学生补齐全科学校成绩 + 补习测验 + 考勤。"""
    rng = random.Random(20260816)
    added_attendance = 0
    added_scores = 0
    added_entry_scores = 0
    skipped_attendance = 0
    skipped_scores = 0
    skipped_entry_scores = 0

    students = db.query(models.Student).all()
    courses = db.query(models.Course).options(joinedload(models.Course.students)).all()

    # 1) 考勤：最近 10 周每门课
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
                tendency = getattr(student, "attendance_tendency", 0.9)
                roll = rng.random()
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
                db.add(models.Attendance(
                    course_id=course.id,
                    student_id=student.id,
                    date=att_date,
                    status=status,
                    notes="",
                ))
                added_attendance += 1

    profiles = build_student_profiles(db, rng)

    # 2) 学校考试：全科覆盖（不限于补习科目），带补习提升规律
    for student in students:
        for subject_id, profile in profiles.get(student.id, {}).items():
            for index, (name, days_ago) in enumerate(SCHOOL_EXAMS):
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
                rate = school_exam_rate(profile, index, rng)
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

    # 3) 补习班测验 + 入班诊断（关联课程）
    for course in courses:
        if course.course_type == "self_study":
            continue
        for student in course.students:
            profile = profiles.get(student.id, {}).get(course.subject_id)
            if not profile:
                continue
            for index, (name, days_ago) in enumerate(zip(QUIZ_NAMES, QUIZ_DAYS_AGO)):
                exam_date = _dow_date(course.day_of_week, days_ago=days_ago)
                exists = db.query(models.ScoreRecord).filter(
                    models.ScoreRecord.student_id == student.id,
                    models.ScoreRecord.course_id == course.id,
                    models.ScoreRecord.exam_name == name,
                    models.ScoreRecord.exam_date == exam_date,
                ).first()
                if exists:
                    skipped_scores += 1
                    continue
                rate = quiz_exam_rate(profile, index, rng)
                db.add(models.ScoreRecord(
                    student_id=student.id,
                    subject_id=course.subject_id,
                    course_id=course.id,
                    exam_type="entry_test" if index == 0 else "quiz",
                    exam_name=name,
                    score=round(rate * 100, 1),
                    max_score=100,
                    exam_date=exam_date,
                    notes="",
                ))
                if index == 0:
                    added_entry_scores += 1
                else:
                    added_scores += 1

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
    "出勤稳定，补习效果明显",
    "近期出勤波动，需关注",
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
    rng = random.Random(20260816)
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
            # 能力分布：约 1/3 基础薄弱，1/2 中等，其余较强
            ability_roll = rng.random()
            if ability_roll < 0.32:
                ability = rng.uniform(0.45, 0.66)
            elif ability_roll < 0.82:
                ability = rng.uniform(0.63, 0.82)
            else:
                ability = rng.uniform(0.80, 0.96)
            # 出勤分布：多数稳定出勤，约 1/4 波动较大（与补习效果负相关）
            tendency = _clamp(0.66 + (ability - 0.52) * 0.62 + rng.uniform(-0.06, 0.06), 0.50, 0.995)
            style = rng.random()
            if style < 0.28:
                tendency = min(0.995, tendency + 0.10)   # 自律型：出勤稳定
            elif style < 0.42:
                tendency = max(0.50, tendency - 0.14)    # 问题型：经常缺勤
            track = ""
            if grade in ("高一", "高二", "高三"):
                track = rng.choice(["文科", "理科"])
            student = models.Student(
                name=name,
                grade_level=grade_level,
                grade=grade,
                track=track,
                phone=f"138{rng.randint(10000000, 99999999)}",
                notes=rng.choice(STUDENT_NOTES),
            )
            db.add(student)
            students.append(student)
            students_by_grade[grade].append(student)
            student.attendance_tendency = tendency
            student.ability = ability
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

    def track_allows_subject(grade: str, track: str, subject_id: int) -> bool:
        if grade not in ("高二", "高三"):
            return True
        return subject_id in ({1, 2, 3} | TRACK_SUBJECTS.get(track, set()))

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
                track = ""
                # 高二/高三只允许开设本方向科目课程
                if grade in ("高二", "高三"):
                    track = rng.choice(["文科", "理科"])
                    if not track_allows_subject(grade, track, subject.id):
                        subject = rng.choice([subjects[i - 1] for i in ({1, 2, 3} | TRACK_SUBJECTS[track])])
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
                if grade in ("高二", "高三"):
                    pool = [
                        s for s in students_by_grade[grade]
                        if s.track == track
                        and track_allows_subject(grade, track, subject.id)
                        and (day, slot) not in occupied[s.id]
                    ]
                    if len(pool) < 2:
                        pool = [
                            s for s in all_students
                            if (s.track == track or s.grade not in ("高二", "高三"))
                            and track_allows_subject(s.grade, s.track, subject.id)
                            and (day, slot) not in occupied[s.id]
                        ]
                else:
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

    # 考勤
    attendance_rows = []
    for course in courses:
        if course.course_type == "self_study":
            continue
        for student in course.students:
            tendency = getattr(student, "attendance_tendency", 0.9)
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

    # 补习科目映射（学生 → 科目集合）
    student_subject_ids = {}
    for course in courses:
        if course.course_type == "self_study":
            continue
        for student in course.students:
            student_subject_ids.setdefault(student.id, set()).add(course.subject_id)

    # 学校成绩（全科）与补习测验（关联课程），共用同一能力档案保证数据自洽
    profiles = {}
    for student in students:
        ability = getattr(student, "ability", 0.8)
        tendency = getattr(student, "attendance_tendency", 0.9)
        tutored = student_subject_ids.get(student.id, set())
        subj = {}
        for subject_id in grade_subject_ids(student):
            base = _clamp(ability + rng.uniform(-0.08, 0.08), 0.30, 0.97)
            subj[subject_id] = {
                "base": base,
                "tutored": subject_id in tutored,
                "tendency": tendency,
            }
        profiles[student.id] = subj

    score_rows = []
    for student in students:
        for subject_id, profile in profiles.get(student.id, {}).items():
            for index, (name, days_ago) in enumerate(SCHOOL_EXAMS):
                rate = school_exam_rate(profile, index, rng)
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
        if course.course_type == "self_study":
            continue
        for student in course.students:
            profile = profiles.get(student.id, {}).get(course.subject_id)
            if not profile:
                continue
            for index, (name, days_ago) in enumerate(zip(QUIZ_NAMES, QUIZ_DAYS_AGO)):
                rate = quiz_exam_rate(profile, index, rng)
                score_rows.append(models.ScoreRecord(
                    student_id=student.id,
                    subject_id=course.subject_id,
                    course_id=course.id,
                    exam_type="entry_test" if index == 0 else "quiz",
                    exam_name=name,
                    score=round(rate * 100, 1),
                    max_score=100,
                    exam_date=_dow_date(course.day_of_week, days_ago=days_ago),
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
