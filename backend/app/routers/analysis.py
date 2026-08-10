import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/analysis", tags=["analysis"])


def _attendance_rate(present: int, late: int, total: int) -> float:
    return round((present + late) / total * 100, 1) if total else 0.0


@router.get("/attendance", response_model=schemas.AttendanceAnalysisOut)
def attendance_analysis(
    student_id: int = None,
    course_id: int = None,
    date_from: date = None,
    date_to: date = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Attendance).options(
        joinedload(models.Attendance.student),
        joinedload(models.Attendance.course).joinedload(models.Course.subject),
    )
    if student_id: q = q.filter(models.Attendance.student_id == student_id)
    if course_id: q = q.filter(models.Attendance.course_id == course_id)
    if date_from: q = q.filter(models.Attendance.date >= date_from)
    if date_to: q = q.filter(models.Attendance.date <= date_to)
    rows = q.all()

    summary = schemas.AttendanceSummary()
    student_map = defaultdict(lambda: {"student": None, "total": 0, "present": 0, "late": 0, "absent": 0, "leave": 0})
    subject_map = {}
    trend_map = {}

    for a in rows:
        summary.total += 1
        if a.status in ("present", "late", "absent", "leave"):
            setattr(summary, a.status, getattr(summary, a.status, 0) + 1)

        key = a.student_id
        stat = student_map[key]
        if stat["student"] is None: stat["student"] = a.student
        stat["total"] += 1
        if a.status in ("present", "late", "absent", "leave"):
            stat[a.status] = stat.get(a.status, 0) + 1

        subj = a.course.subject if a.course else None
        if subj:
            skey = subj.id
            if skey not in subject_map:
                subject_map[skey] = {"subject_id": skey, "subject": subj, "total": 0, "present": 0, "late": 0, "absent": 0, "leave": 0}
            sstat = subject_map[skey]
            sstat["total"] += 1
            if a.status in ("present", "late", "absent", "leave"):
                sstat[a.status] = sstat.get(a.status, 0) + 1

        if a.date not in trend_map:
            trend_map[a.date] = schemas.AttendanceTrendPoint(date_val=a.date)
        tp = trend_map[a.date]
        tp.total += 1
        if a.status == "present": tp.present += 1
        elif a.status == "late": tp.late += 1

    summary.rate = _attendance_rate(summary.present, summary.late, summary.total)
    student_stats = []
    for st in student_map.values():
        rate = _attendance_rate(st["present"], st["late"], st["total"])
        student_stats.append(schemas.StudentAttendanceStat(
            student=st["student"], total=st["total"], present=st["present"],
            late=st["late"], absent=st["absent"], leave=st["leave"], rate=rate))
    subject_stats = []
    for st in subject_map.values():
        rate = _attendance_rate(st["present"], st["late"], st["total"])
        subject_stats.append(schemas.SubjectAttendanceStat(
            subject_id=st["subject_id"], subject=st["subject"], total=st["total"],
            present=st["present"], late=st["late"], absent=st["absent"], leave=st["leave"], rate=rate))
    for tp in trend_map.values():
        tp.rate = _attendance_rate(tp.present, tp.late, tp.total)

    return schemas.AttendanceAnalysisOut(
        summary=summary,
        by_student=sorted(student_stats, key=lambda x: (x.rate, x.total), reverse=True),
        by_subject=sorted(subject_stats, key=lambda x: x.rate, reverse=True),
        trend=sorted(trend_map.values(), key=lambda x: x.date_val),
    )


@router.get("/scores", response_model=schemas.ScoreAnalysisOut)
def score_analysis(
    student_id: int = None,
    subject_id: int = None,
    exam_type: str = None,
    date_from: date = None,
    date_to: date = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.ScoreRecord).options(
        joinedload(models.ScoreRecord.student),
        joinedload(models.ScoreRecord.subject),
    )
    if student_id: q = q.filter(models.ScoreRecord.student_id == student_id)
    if subject_id: q = q.filter(models.ScoreRecord.subject_id == subject_id)
    if exam_type: q = q.filter(models.ScoreRecord.exam_type == exam_type)
    if date_from: q = q.filter(models.ScoreRecord.exam_date >= date_from)
    if date_to: q = q.filter(models.ScoreRecord.exam_date <= date_to)
    rows = q.order_by(models.ScoreRecord.exam_date, models.ScoreRecord.id).all()

    summary = schemas.ScoreSummary()
    subject_map = defaultdict(lambda: {
        "subject_id": 0, "subject": None, "total": 0,
        "school_count": 0, "quiz_count": 0, "entry_count": 0, "avg_score": 0.0, "avg_rate": 0.0,
        "best_rate": 0.0, "lowest_rate": None,
    })
    student_map = defaultdict(lambda: {
        "student": None, "total": 0, "avg_score": 0.0, "avg_rate": 0.0,
        "school": [], "quiz": [], "entry": [], "best": 0.0, "lowest": None,
    })
    trend = []

    for r in rows:
        rate = r.rate
        summary.total += 1
        if r.exam_type == "school_exam": summary.school_count += 1
        elif r.exam_type == "entry_test": summary.entry_count += 1
        else: summary.quiz_count += 1
        summary.avg_score += r.score
        summary.avg_rate += rate
        summary.best_rate = max(summary.best_rate, rate)
        summary.lowest_rate = min(summary.lowest_rate, rate) if summary.lowest_rate else rate

        sstat = subject_map[r.subject_id]
        if sstat["subject"] is None:
            sstat["subject_id"] = r.subject_id
            sstat["subject"] = r.subject
        sstat["total"] += 1
        if r.exam_type == "school_exam": sstat["school_count"] += 1
        elif r.exam_type == "entry_test": sstat["entry_count"] += 1
        else: sstat["quiz_count"] += 1
        sstat["avg_score"] += r.score
        sstat["avg_rate"] += rate
        sstat["best_rate"] = max(sstat["best_rate"], rate)
        sstat["lowest_rate"] = min(sstat["lowest_rate"], rate) if sstat["lowest_rate"] is not None else rate

        st = student_map[r.student_id]
        if st["student"] is None: st["student"] = r.student
        st["total"] += 1
        st["avg_score"] += r.score
        st["avg_rate"] += rate
        if r.exam_type == "school_exam": st["school"].append(rate)
        elif r.exam_type == "entry_test": st["entry"].append(rate)
        else: st["quiz"].append(rate)
        st["best"] = max(st["best"], rate)
        st["lowest"] = min(st["lowest"], rate) if st["lowest"] is not None else rate

        trend.append(schemas.ScoreTrendPoint(
            id=r.id,
            exam_date=r.exam_date,
            exam_name=r.exam_name,
            exam_type=r.exam_type,
            subject_id=r.subject_id,
            subject=r.subject,
            score=r.score,
            max_score=r.max_score,
            rate=rate,
        ))

    if summary.total:
        summary.avg_score = round(summary.avg_score / summary.total, 1)
        summary.avg_rate = round(summary.avg_rate / summary.total, 1)
    subject_stats = []
    for st in subject_map.values():
        if st["total"]:
            st["avg_score"] = round(st["avg_score"] / st["total"], 1)
            st["avg_rate"] = round(st["avg_rate"] / st["total"], 1)
        subject_stats.append(schemas.SubjectScoreStat(
            subject_id=st["subject_id"], subject=st["subject"],
            total=st["total"], school_count=st["school_count"], quiz_count=st["quiz_count"], entry_count=st["entry_count"],
            avg_score=st["avg_score"], avg_rate=st["avg_rate"],
            best_rate=st["best_rate"], lowest_rate=st["lowest_rate"] or 0.0,
        ))
    student_stats = []
    for st in student_map.values():
        if st["total"]:
            st["avg_score"] = round(st["avg_score"] / st["total"], 1)
            st["avg_rate"] = round(st["avg_rate"] / st["total"], 1)
        student_stats.append(schemas.StudentScoreStat(
            student=st["student"],
            total=st["total"],
            avg_score=st["avg_score"],
            avg_rate=st["avg_rate"],
            school_avg_rate=round(sum(st["school"]) / len(st["school"]), 1) if st["school"] else 0.0,
            quiz_avg_rate=round(sum(st["quiz"]) / len(st["quiz"]), 1) if st["quiz"] else 0.0,
            entry_avg_rate=round(sum(st["entry"]) / len(st["entry"]), 1) if st["entry"] else 0.0,
            best_rate=st["best"],
            lowest_rate=st["lowest"] or 0.0,
        ))

    return schemas.ScoreAnalysisOut(
        summary=summary,
        by_subject=sorted(subject_stats, key=lambda x: x.avg_rate, reverse=True),
        by_student=sorted(student_stats, key=lambda x: x.avg_rate, reverse=True),
        trend=trend,
    )


@router.get("/radar/{student_id}", response_model=schemas.RadarOut)
def radar_chart(student_id: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student: raise HTTPException(status_code=404, detail="Student not found")

    scores = db.query(models.ScoreRecord).options(
        joinedload(models.ScoreRecord.subject)
    ).filter(models.ScoreRecord.student_id == student_id).all()
    attendances = db.query(models.Attendance).options(
        joinedload(models.Attendance.course)
    ).filter(models.Attendance.student_id == student_id).all()

    score_map = defaultdict(lambda: {"total": 0, "school": [], "quiz": [], "entry": []})
    for s in scores:
        item = score_map[s.subject_id]
        item["subject"] = s.subject
        item["total"] += 1
        if s.exam_type == "school_exam": item["school"].append(s.rate)
        elif s.exam_type == "entry_test": item["entry"].append(s.rate)
        else: item["quiz"].append(s.rate)

    att_map = defaultdict(lambda: {"total": 0, "present": 0, "late": 0})
    for a in attendances:
        if not a.course or a.course.subject_id is None: continue
        item = att_map[a.course.subject_id]
        item["total"] += 1
        if a.status == "present": item["present"] += 1
        elif a.status == "late": item["late"] += 1

    axes = []
    for subj_id, item in score_map.items():
        att = att_map.get(subj_id, {"total": 0, "present": 0, "late": 0})
        axes.append(schemas.RadarAxis(
            subject_id=subj_id,
            subject=item["subject"].name if item["subject"] else "未知",
            record_count=item["total"],
            school_avg_rate=round(sum(item["school"]) / len(item["school"]), 1) if item["school"] else 0.0,
            quiz_avg_rate=round(sum(item["quiz"]) / len(item["quiz"]), 1) if item["quiz"] else 0.0,
            entry_avg_rate=round(sum(item["entry"]) / len(item["entry"]), 1) if item["entry"] else 0.0,
            overall_avg_rate=round(
                (sum(item["school"]) + sum(item["quiz"]) + sum(item["entry"])) / item["total"], 1
            ) if item["total"] else 0.0,
            attendance_rate=_attendance_rate(att["present"], att["late"], att["total"]),
        ))
    axes.sort(key=lambda x: x.subject_id)
    return schemas.RadarOut(student=student, axes=axes)


def _get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(models.AppSetting).filter(models.AppSetting.key == key).first()
    return row.value if row and row.value else default


def _load_student_context(db: Session, student_id: int) -> dict:
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student: raise HTTPException(status_code=404, detail="Student not found")
    courses = db.query(models.Course).join(models.Course.students).filter(
        models.Student.id == student_id
    ).options(joinedload(models.Course.subject), joinedload(models.Course.teacher)).all()
    att = attendance_analysis(student_id=student_id, db=db)
    sc = score_analysis(student_id=student_id, db=db)
    radar = radar_chart(student_id, db)
    return {
        "student": student,
        "courses": courses,
        "attendance": att,
        "scores": sc,
        "radar": radar,
    }


def _build_prompt(ctx: dict) -> str:
    s = ctx["student"]
    att = ctx["attendance"]
    sc = ctx["scores"]
    radar = ctx["radar"]
    courses = [f"{c.name}（{c.subject.name if c.subject else '-'} / {c.teacher.name if c.teacher else '-'}）" for c in ctx["courses"]]
    att_subj = "\n".join(
        f"- {x.subject.name}: 出勤率 {x.rate}%（出勤{x.present}，迟到{x.late}，缺勤{x.absent}，请假{x.leave}，共{x.total}次）"
        for x in att.by_subject[:10]
    ) or "- 暂无"
    score_subj = "\n".join(
        f"- {x.subject.name}: 平均{x.avg_rate}%（学校考试{x.school_count}次 / 小测验{x.quiz_count}次 / 入班诊断{x.entry_count}次，最高{x.best_rate}%，最低{x.lowest_rate}%）"
        for x in sc.by_subject[:10]
    ) or "- 暂无"
    radar_lines = "\n".join(
        f"- {x.subject}: 课前诊断{x.entry_avg_rate}% → 课后测验{x.quiz_avg_rate}%（变化{(x.quiz_avg_rate - x.entry_avg_rate):+.1f}pp），学校考试{x.school_avg_rate}%，出勤{x.attendance_rate}%"
        for x in radar.axes[:8]
    ) or "- 暂无"
    trend = "\n".join(
        f"- {t.exam_date} {t.subject.name} {t.exam_name}（{_exam_type_label(t.exam_type)}）：{t.score}/{t.max_score} = {t.rate}%"
        for t in sc.trend[-15:]
    ) or "- 暂无"
    return f"""请严格依据下方数据，为这名补习班学生生成一份中文学习分析报告。

【硬性要求】
1. 只允许使用下方提供的数据，禁止编造、推测任何未给出的信息（例如考试性质、升学目标、家庭情况、教师评价等）。
2. 输出固定 Markdown 结构，不得增减章节：
   # {s.name}学习分析报告
   ## 一、总体评价
   ## 二、学科强弱项
   ## 三、课前课后对比
   ## 四、进步趋势
   ## 五、出勤表现
   ## 六、针对性建议
3. 每条结论必须引用具体数字（得分率、次数、变化量），禁止空泛套话。
4. 学科强弱项按平均得分率排序，并明确标注"优势/中等/薄弱"。
5. 课前课后对比必须逐科写明"课前诊断得分率 → 课后测验得分率"及差值，再总结进步最大和退步/无进步的科目。
6. 针对性建议按优先级列出 3-5 条，每条必须对应上文某条数据，不能脱离数据。
7. 全文 800-1200 字，用第三人称"该生/该学生"，不要写"根据提供的数据"这类元话语。
8. 禁止虚构百分比、次数、课程名；所有数值必须与下方数据一致。

学生：{s.name}，{s.grade_level}{s.grade}
在读课程：{'、'.join(courses) or '暂无'}

【考勤数据】
汇总：共{att.summary.total}次，出勤{att.summary.present}，迟到{att.summary.late}，缺勤{att.summary.absent}，请假{att.summary.leave}，出勤率{att.summary.rate}%
分科出勤：
{att_subj}

【成绩数据】
汇总：共{sc.summary.total}条（学校考试{sc.summary.school_count} / 小测验{sc.summary.quiz_count} / 入班诊断{sc.summary.entry_count}），平均得分率{sc.summary.avg_rate}%，最高{sc.summary.best_rate}%，最低{sc.summary.lowest_rate}%
分科成绩：
{score_subj}

【课前课后对比（百分制）】
{radar_lines}

【最近考试/测验记录（按时间倒序，最多15条）】
{trend}"""


def _exam_type_label(exam_type: str) -> str:
    return {
        "school_exam": "学校考试",
        "quiz": "补习班小测验",
        "entry_test": "入班诊断",
    }.get(exam_type, exam_type)


def _call_deepseek(api_key: str, base_url: str, model: str, prompt: str) -> tuple[str, str]:
    url = base_url.rstrip("/") + "/chat/completions"
    candidates = [model] if model == "deepseek-chat" else [model, "deepseek-chat"]
    for candidate in candidates:
        for attempt in range(2):
            payload = json.dumps({
                "model": candidate,
                "messages": [
                    {"role": "system", "content": "你是课外辅导机构的教务数据分析助手。你只能根据用户提供的数据撰写报告：不得编造或推测数据，不得添加数据中不存在的背景信息，必须使用固定 Markdown 章节结构，每个结论都要有数字支撑，语言客观、专业、简洁。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 2400,
                "stream": False,
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")[:500]
                if e.code in (402, 403, 429):
                    raise HTTPException(status_code=429, detail=f"DeepSeek 请求受限或额度不足（{e.code}）：{body}")
                raise HTTPException(status_code=502, detail=f"DeepSeek API 调用失败（{e.code}）：{body}")
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"DeepSeek API 连接失败：{e}")
            try:
                content = data["choices"][0]["message"].get("content") or ""
            except Exception:
                raise HTTPException(status_code=502, detail="DeepSeek API 返回格式异常")
            if content.strip():
                return content, candidate
            if attempt == 0:
                continue
    raise HTTPException(status_code=502, detail="DeepSeek 连续返回空报告，已尝试回退 deepseek-chat 仍未成功，请检查 API Key、模型配置或额度")


@router.post("/ai-report", response_model=schemas.AiReportOut)
def ai_report(body: schemas.AiReportRequest, db: Session = Depends(get_db)):
    api_key = body.api_key or os.environ.get("DEEPSEEK_API_KEY") or _get_setting(db, "deepseek_api_key")
    if not api_key:
        raise HTTPException(status_code=400, detail="尚未配置 DeepSeek API Key，请先在设置中填写")
    model = body.model or _get_setting(db, "deepseek_model", "deepseek-chat")
    base_url = _get_setting(db, "deepseek_base_url", "https://api.deepseek.com")
    ctx = _load_student_context(db, body.student_id)
    prompt = _build_prompt(ctx)
    report, used_model = _call_deepseek(api_key, base_url, model, prompt)
    model = used_model
    now = datetime.now()
    db.add(models.AiReport(
        student_id=body.student_id,
        report=report,
        model=model,
        generated_at=now,
    ))
    db.commit()
    return schemas.AiReportOut(
        student_id=body.student_id,
        report=report,
        model=model,
        generated_at=now.isoformat(timespec="seconds"),
    )


@router.get("/ai-report/{student_id}", response_model=schemas.AiReportOut)
def latest_ai_report(student_id: int, db: Session = Depends(get_db)):
    if not db.query(models.Student).filter(models.Student.id == student_id).first():
        raise HTTPException(status_code=404, detail="Student not found")
    rec = db.query(models.AiReport).filter(
        models.AiReport.student_id == student_id
    ).order_by(models.AiReport.generated_at.desc(), models.AiReport.id.desc()).first()
    if not rec:
        raise HTTPException(status_code=404, detail="该学生暂无已保存的 AI 报告，请先生成")
    return schemas.AiReportOut(
        student_id=student_id,
        report=rec.report,
        model=rec.model,
        generated_at=rec.generated_at.strftime("%Y-%m-%d %H:%M:%S") if rec.generated_at else "",
    )


def _course_out(c: models.Course) -> schemas.CourseOut:
    c.student_count = len(c.students)
    return schemas.CourseOut.model_validate(c, from_attributes=True)


@router.get("/dashboard", response_model=schemas.DashboardOut)
def dashboard_overview(db: Session = Depends(get_db)):
    courses = db.query(models.Course).options(
        joinedload(models.Course.subject),
        joinedload(models.Course.teacher),
        joinedload(models.Course.room),
        joinedload(models.Course.students),
    ).all()
    for c in courses:
        c.student_count = len(c.students)

    today = date.today()
    dow = today.weekday()
    today_courses = [c for c in courses if c.day_of_week == dow]
    att = attendance_analysis(db=db)
    sc = score_analysis(db=db)
    today_att_rows = db.query(models.Attendance).filter(models.Attendance.date == today).all()
    today_att = {"total": 0, "present": 0, "late": 0, "absent": 0, "leave": 0}
    for a in today_att_rows:
        today_att["total"] += 1
        if a.status in today_att:
            today_att[a.status] += 1

    weekly_load = [sum(1 for c in courses if c.day_of_week == i) for i in range(7)]
    slot_load = [sum(1 for c in courses if c.time_slot == i) for i in range(1, 6)]

    rooms = db.query(models.Room).order_by(models.Room.id).all()
    room_occupancy = []
    for room in rooms:
        rc = [c for c in today_courses if c.room_id == room.id]
        room_occupancy.append(schemas.RoomOccupancyOut(
            room_id=room.id,
            room_name=room.name,
            room_type=room.room_type,
            today_courses=len(rc),
            today_students=sum(len(c.students) for c in rc),
        ))

    subjects = db.query(models.Subject).order_by(models.Subject.id).all()
    subject_metrics = []
    for subject in subjects:
        subj_courses = [c for c in courses if c.subject_id == subject.id]
        student_ids = set()
        for c in subj_courses:
            student_ids.update(s.id for s in c.students)
        att_stat = next((x for x in att.by_subject if x.subject_id == subject.id), None)
        score_stat = next((x for x in sc.by_subject if x.subject_id == subject.id), None)
        subject_metrics.append(schemas.SubjectMetricOut(
            subject_id=subject.id,
            subject=subject.name,
            course_count=len(subj_courses),
            student_count=len(student_ids),
            attendance_rate=att_stat.rate if att_stat else 0.0,
            score_rate=score_stat.avg_rate if score_stat else 0.0,
        ))

    score_trend_map = {}
    for t in sc.trend:
        key = t.exam_date.isoformat()
        item = score_trend_map.setdefault(key, {"date_val": key, "avg_rate": 0.0, "count": 0})
        item["avg_rate"] = (item["avg_rate"] * item["count"] + t.rate) / (item["count"] + 1)
        item["count"] += 1
    score_trend = [
        schemas.ScoreTrendPointOut(**v)
        for v in sorted(score_trend_map.values(), key=lambda x: x["date_val"])[-20:]
    ]

    adjustments = db.query(models.ScheduleAdjustment).options(
        joinedload(models.ScheduleAdjustment.course)
    ).order_by(models.ScheduleAdjustment.created_at.desc(), models.ScheduleAdjustment.id.desc()).limit(5).all()

    return schemas.DashboardOut(
        counts=schemas.DashboardCounts(
            students=db.query(models.Student).count(),
            teachers=db.query(models.Teacher).count(),
            courses=len(courses),
            subjects=len(subjects),
            rooms=len(rooms),
        ),
        today_date=today.isoformat(),
        today_dow=dow,
        today_courses=[_course_out(c) for c in sorted(today_courses, key=lambda c: (c.time_slot, c.room_id))],
        today_student_seats=sum(len(c.students) for c in today_courses),
        today_attendance=schemas.TodayAttendanceOut(**today_att),
        weekly_load=weekly_load,
        slot_load=slot_load,
        room_occupancy=room_occupancy,
        attendance=att.summary,
        scores=sc.summary,
        subject_metrics=subject_metrics,
        attendance_trend=att.trend[-14:],
        score_trend=score_trend,
        adjustments=[schemas.AdjustmentOut.model_validate(a) for a in adjustments],
    )


@router.get("/course-health", response_model=list[schemas.CourseHealthOut])
def course_health(db: Session = Depends(get_db)):
    courses = db.query(models.Course).options(
        joinedload(models.Course.subject),
        joinedload(models.Course.teacher),
        joinedload(models.Course.room),
        joinedload(models.Course.students),
    ).all()
    for c in courses:
        c.student_count = len(c.students)

    att_map = defaultdict(lambda: {"total": 0, "present": 0, "late": 0, "absent": 0, "leave": 0})
    for a in db.query(models.Attendance).all():
        item = att_map[a.course_id]
        item["total"] += 1
        if a.status in item:
            item[a.status] += 1

    score_map = defaultdict(list)
    for r in db.query(models.ScoreRecord).order_by(models.ScoreRecord.exam_date, models.ScoreRecord.id).all():
        if r.course_id:
            score_map[r.course_id].append(r.rate)

    teacher_load = defaultdict(int)
    for c in courses:
        teacher_load[c.teacher_id] += 1

    results = []
    for c in courses:
        att = att_map[c.id]
        att_rate = _attendance_rate(att["present"], att["late"], att["total"]) if att["total"] else 0.0
        rates = score_map.get(c.id, [])
        score_rate = round(sum(rates) / len(rates), 1) if rates else 0.0
        utilization = round(c.student_count / c.max_students * 100, 1) if c.max_students else 0.0
        load = teacher_load.get(c.teacher_id, 0)
        trend_delta = 0.0
        if len(rates) >= 2:
            half = len(rates) // 2
            first = sum(rates[:half]) / half
            second = sum(rates[half:]) / (len(rates) - half)
            trend_delta = round(second - first, 1)

        load_score = min(1.0, utilization / 100)
        fit = max(0.0, 1 - abs(utilization - 85) / 85)
        teacher_fit = max(0.0, 1 - max(0, load - 5) / 5)
        if att["total"] or rates:
            health = round(att_rate * 0.34 + score_rate * 0.30 + load_score * 22 + fit * 8 + teacher_fit * 6, 1)
        else:
            health = round(50 + load_score * 30 + fit * 10 + teacher_fit * 10, 1)

        signals = []
        if utilization >= 100:
            signals.append("满员")
        elif utilization >= 85:
            signals.append("接近满员")
        elif utilization <= 40:
            signals.append("空置率偏高")
        if att["total"] and att_rate < 85:
            signals.append("出勤偏低")
        if rates and score_rate < 70:
            signals.append("成绩偏低")
        if trend_delta < -5:
            signals.append("成绩下滑")
        if load >= 7:
            signals.append("教师课量偏高")
        risk_level = "high" if health < 65 else ("medium" if health < 80 else "low")

        results.append(schemas.CourseHealthOut(
            course_id=c.id,
            name=c.name,
            subject=c.subject.name if c.subject else "—",
            teacher=c.teacher.name if c.teacher else "—",
            room=c.room.name if c.room else "—",
            day=c.day_of_week,
            slot=c.time_slot,
            students=c.student_count,
            max_students=c.max_students,
            attendance_rate=att_rate,
            score_rate=score_rate,
            utilization=utilization,
            health_score=health,
            risk_level=risk_level,
            signals=signals,
            trend_delta=trend_delta,
            teacher_load=load,
        ))

    results.sort(key=lambda x: x.health_score)
    return results


@router.get("/risk", response_model=list[schemas.RiskStudentOut])
def risk_students(db: Session = Depends(get_db)):
    students = db.query(models.Student).all()
    att_map = defaultdict(lambda: {"total": 0, "present": 0, "late": 0, "absent": 0, "leave": 0})
    student_courses = defaultdict(set)
    recent_absences = defaultdict(int)
    today = date.today()
    for a in db.query(models.Attendance).all():
        item = att_map[a.student_id]
        item["total"] += 1
        if a.status in item:
            item[a.status] += 1
        student_courses[a.student_id].add(a.course_id)
        if a.status == "absent" and (today - a.date).days <= 30:
            recent_absences[a.student_id] += 1

    score_map = defaultdict(list)
    for r in db.query(models.ScoreRecord).order_by(models.ScoreRecord.exam_date, models.ScoreRecord.id).all():
        score_map[r.student_id].append(r.rate)

    results = []
    for s in students:
        att = att_map[s.id]
        att_rate = _attendance_rate(att["present"], att["late"], att["total"]) if att["total"] else 0.0
        rates = score_map.get(s.id, [])
        score_rate = round(sum(rates) / len(rates), 1) if rates else 0.0
        trend_delta = 0.0
        if len(rates) >= 2:
            half = len(rates) // 2
            first = sum(rates[:half]) / half
            second = sum(rates[half:]) / (len(rates) - half)
            trend_delta = round(second - first, 1)

        risk = 0.0
        signals = []
        if att["total"] and att_rate < 85:
            risk += 30
            signals.append("出勤率低于85%")
        if att["total"] and att_rate < 70:
            risk += 15
            signals.append("出勤率低于70%")
        if rates and score_rate < 70:
            risk += 25
            signals.append("平均得分率低于70%")
        if rates and score_rate < 60:
            risk += 10
        if trend_delta < -5:
            risk += 15
            signals.append("成绩近期下滑")
        abs_count = recent_absences[s.id]
        if abs_count >= 2:
            risk += 15
            signals.append(f"近30天缺勤{abs_count}次")
        if not rates:
            risk += 12
            signals.append("暂无成绩记录")
        if len(student_courses.get(s.id, set())) == 0:
            risk += 10
            signals.append("未关联课程")

        risk = round(min(risk, 99), 1)
        risk_level = "high" if risk >= 70 else ("medium" if risk >= 40 else "low")
        results.append(schemas.RiskStudentOut(
            student_id=s.id,
            name=s.name,
            grade=s.grade,
            grade_level=s.grade_level,
            attendance_rate=att_rate,
            score_rate=score_rate,
            trend_delta=trend_delta,
            recent_absences=abs_count,
            courses=len(student_courses.get(s.id, set())),
            risk_score=risk,
            risk_level=risk_level,
            signals=signals,
        ))

    results.sort(key=lambda x: x.risk_score, reverse=True)
    return results


def _build_ai_context(db: Session) -> dict:
    return {
        "dashboard": dashboard_overview(db),
        "health": course_health(db),
        "risk": risk_students(db),
    }


def _build_ai_prompt(ctx: dict, insight_type: str, question: str, history: list) -> str:
    dash = ctx["dashboard"]
    health = ctx["health"]
    risk = ctx["risk"]
    d = dash

    def _pct(v: float) -> str:
        return f"{v:.1f}%" if v else "暂无"

    weekly = "、".join(f"周{['一','二','三','四','五','六','日'][i]} {d.weekly_load[i]}节" for i in range(7))
    slot = "、".join(f"时段{i+1} {d.slot_load[i]}节" for i in range(5))
    subjects = "；".join(
        f"{m.subject}（{m.course_count}门课，{m.student_count}名学生，出勤{_pct(m.attendance_rate)}，成绩{_pct(m.score_rate)}）"
        for m in d.subject_metrics
    ) or "暂无"
    att_trend = "；".join(
        f"{t.date_val} {t.total}次，出勤率{_pct(t.rate)}"
        for t in d.attendance_trend[-10:]
    ) or "暂无"
    score_trend = "；".join(
        f"{t.date_val} 平均得分率{_pct(t.avg_rate)}（{t.count}条）"
        for t in d.score_trend[-10:]
    ) or "暂无"
    health_lines = "\n".join(
        f"- {h.name}（{h.subject}/{h.teacher}）：健康度{h.health_score}，出勤{_pct(h.attendance_rate)}，成绩{_pct(h.score_rate)}，满员率{h.utilization:.0f}%，教师周课量{h.teacher_load}，{('、'.join(h.signals) or '暂无信号')}"
        for h in health[:12]
    ) or "- 暂无"
    risk_lines = "\n".join(
        f"- {r.name}（{r.grade_level}{r.grade}）：风险分{r.risk_score}，出勤{_pct(r.attendance_rate)}，成绩{_pct(r.score_rate)}，近30天缺勤{r.recent_absences}次，{('、'.join(r.signals) or '暂无信号')}"
        for r in risk[:12]
    ) or "- 暂无"

    base = f"""
你是一个培训机构教务数据助手。只能使用下方提供的数据进行分析，禁止编造数据、人数、课程、百分比或背景信息。

【机构总览】
学生{d.counts.students}人，教师{d.counts.teachers}人，课程{d.counts.courses}门，科目{d.counts.subjects}科，教室{d.counts.rooms}间。
今日（{d.today_date}）课程{d.today_courses.__len__()}节，覆盖{d.today_student_seats}人次；今日考勤：出勤{d.today_attendance.present}，迟到{d.today_attendance.late}，缺勤{d.today_attendance.absent}，请假{d.today_attendance.leave}。
整体出勤率{_pct(d.attendance.rate)}，成绩平均得分率{_pct(d.scores.avg_rate)}。
周负载：{weekly}。
时段负载：{slot}。
分科情况：{subjects}
出勤趋势：{att_trend}
成绩趋势：{score_trend}

【课程健康度（按健康度从低到高）】
{health_lines}

【学生风险榜（按风险分从高到低）】
{risk_lines}
"""

    if insight_type == "risk":
        return base + """
请生成一份"学生流失与学业风险分析"，固定输出以下 Markdown 章节：
# 学生风险分析
## 一、风险总览
## 二、高风险学生
## 三、中风险学生
## 四、共同信号
## 五、干预建议
要求：每个结论引用具体数字；高风险/中风险学生按风险分排序并说明原因；干预建议 3-6 条，必须可落地。
"""
    if insight_type == "schedule":
        return base + """
请生成一份"排课与资源优化建议"，固定输出以下 Markdown 章节：
# 排课优化建议
## 一、当前负载
## 二、教室与时段瓶颈
## 三、教师负载
## 四、优化建议
## 五、风险提示
要求：只依据提供的数据；每条建议写明具体对象（星期/时段/课程/教师）；不得虚构空教室或空闲时段。
"""
    if insight_type == "qa":
        q = question.strip() or "请根据当前数据，给出一份简要的机构经营诊断"
        history_lines = "\n".join(
            f"{'用户' if m.get('role') == 'user' else '助手'}：{m.get('content', '')}"
            for m in history[-8:]
        )
        return base + f"""
以下是对话历史：
{history_lines or '暂无'}

用户的新问题：{q}
请用中文回答。若数据无法回答，必须明确说明"现有数据无法判断"，再给出可用数据范围内的相关结论。回答控制在 600 字以内，可使用简洁 Markdown 列表。
"""
    return base + """
请生成一份"机构运营健康报告"，固定输出以下 Markdown 章节：
# 机构运营健康报告
## 一、总体评分
## 二、规模与负载
## 三、学科表现
## 四、课程健康
## 五、风险预警
## 六、改进建议
要求：每条结论引用具体数字；总体评分需给出 0-100 分和评分依据；改进建议 4-6 条。
"""


@router.post("/ai-insight", response_model=schemas.AiInsightOut)
def ai_insight(body: schemas.AiInsightRequest, db: Session = Depends(get_db)):
    api_key = body.api_key or os.environ.get("DEEPSEEK_API_KEY") or _get_setting(db, "deepseek_api_key")
    if not api_key:
        raise HTTPException(status_code=400, detail="尚未配置 DeepSeek API Key，请先在设置中填写")
    model = body.model or _get_setting(db, "deepseek_model", "deepseek-chat")
    base_url = _get_setting(db, "deepseek_base_url", "https://api.deepseek.com")
    ctx = _build_ai_context(db)
    prompt = _build_ai_prompt(ctx, body.insight_type, body.question, body.history)
    answer, used_model = _call_deepseek(api_key, base_url, model, prompt)
    now = datetime.now()
    return schemas.AiInsightOut(
        answer=answer,
        model=used_model,
        generated_at=now.isoformat(timespec="seconds"),
    )


def _markdown_to_pdf_paragraphs(text: str) -> list:
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        font_name = "STSong-Light"
    except Exception:
        font_name = "Helvetica"

    styles = {
        "h1": ParagraphStyle("h1", fontName=font_name, fontSize=18, leading=24, spaceAfter=10, textColor=colors.HexColor("#1e293b")),
        "h2": ParagraphStyle("h2", fontName=font_name, fontSize=15, leading=20, spaceBefore=8, spaceAfter=6, textColor=colors.HexColor("#334155")),
        "h3": ParagraphStyle("h3", fontName=font_name, fontSize=13, leading=17, spaceBefore=6, spaceAfter=4, textColor=colors.HexColor("#475569")),
        "p": ParagraphStyle("p", fontName=font_name, fontSize=11, leading=18, spaceAfter=6, alignment=TA_LEFT),
        "li": ParagraphStyle("li", fontName=font_name, fontSize=11, leading=18, leftIndent=16, spaceAfter=4, bulletIndent=4),
    }
    paras = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("###"):
            paras.append(Paragraph(line.lstrip("#").strip(), styles["h3"]))
        elif line.startswith("##"):
            paras.append(Paragraph(line.lstrip("#").strip(), styles["h2"]))
        elif line.startswith("#"):
            paras.append(Paragraph(line.lstrip("#").strip(), styles["h1"]))
        elif line.startswith("-") or line.startswith("*"):
            paras.append(Paragraph(line.lstrip("-* ").strip(), styles["li"], bulletText="•"))
        else:
            paras.append(Paragraph(line, styles["p"]))
    return paras


@router.get("/ai-report/{student_id}/pdf")
def ai_report_pdf(student_id: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    rec = db.query(models.AiReport).filter(
        models.AiReport.student_id == student_id
    ).order_by(models.AiReport.generated_at.desc(), models.AiReport.id.desc()).first()
    if not rec:
        raise HTTPException(status_code=404, detail="该学生暂无已保存的 AI 报告，请先生成")

    from io import BytesIO
    from reportlab.platypus import SimpleDocTemplate
    from reportlab.lib.pagesizes import A4

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=48, rightMargin=48, topMargin=48, bottomMargin=48)
    doc.build(_markdown_to_pdf_paragraphs(rec.report))
    filename = f"{student.name}_学习分析报告_{date.today().strftime('%Y%m%d')}.pdf"
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"
        },
    )
