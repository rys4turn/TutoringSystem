# -*- coding: utf-8 -*-
"""
择校冲刺分析：
- 内置 2026 年苏州中考 / 江苏高考分数线（admission_lines 表）；
- 按年级给出不同阶段分析（初中基础期/中考冲刺期/高中基础期/高中提升期/高考冲刺期）；
- 根据学生最近学校考试成绩加权估算中考/高考总分，对照分数线定位“冲刺/稳妥/保底”学校；
- 输出分科提分空间与学习建议；可选调用 DeepSeek 生成 AI 冲刺分析报告。
"""
import json
import os
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/analysis", tags=["roadmap"])


ZHONGKAO_WEIGHTS = {
    "语文": 130, "数学": 130, "英语": 130,
    "物理": 100, "化学": 100, "政治": 50, "历史": 50,
}
ZHONGKAO_FULL = 740
TIYU_BASE = 44.0

GAOKAO_WEIGHTS = {
    "语文": 150, "数学": 150, "英语": 150,
    "物理": 100, "化学": 100, "生物": 100,
    "政治": 100, "历史": 100, "地理": 100,
}
GAOKAO_FULL = 750
TRACK_FIRST = {"文科": "历史", "理科": "物理"}

STAGE_META = {
    "初一": ("初中基础期", "zhongkao", "苏州"),
    "初二": ("初中基础期", "zhongkao", "苏州"),
    "初三": ("中考冲刺期", "zhongkao", "苏州"),
    "高一": ("高中基础期", "gaokao", "江苏"),
    "高二": ("高中提升期", "gaokao", "江苏"),
    "高三": ("高考冲刺期", "gaokao", "江苏"),
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _round1(v: float) -> float:
    return round(v, 1)


def _student_school_rates(db: Session, student_id: int) -> tuple[dict, dict]:
    """返回 (最新得分率 per subject, 趋势 subject -> [(days_ago, rate)])。"""
    rows = db.query(models.ScoreRecord).options(
        joinedload(models.ScoreRecord.subject),
    ).filter(
        models.ScoreRecord.student_id == student_id,
        models.ScoreRecord.exam_type == "school_exam",
    ).all()
    latest = {}
    trend = defaultdict(list)
    today = date.today()
    for r in rows:
        days_ago = max(0, (today - r.exam_date).days)
        trend[r.subject_id].append((days_ago, r.rate))
        if r.subject_id not in latest or days_ago < latest[r.subject_id][0]:
            latest[r.subject_id] = (days_ago, r.rate, r)
    return latest, trend


def _subject_name(db: Session, subject_id: int) -> str:
    s = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    return s.name if s else f"科目{subject_id}"


def _months_to_exam(today: date, exam_type: str) -> float:
    if exam_type == "zhongkao":
        target = date(today.year, 6, 20)
        if target < today:
            target = date(today.year + 1, 6, 20)
    else:
        target = date(today.year, 6, 7)
        if target < today:
            target = date(today.year + 1, 6, 7)
    return max(0.5, (target - today).days / 30.0)


def _trend_slope_pp(points: list[tuple[int, float]]) -> float:
    """根据 (days_ago, rate) 计算每月得分率变化（pp/月）。"""
    if len(points) < 2:
        return 0.0
    ordered = sorted(points, key=lambda x: -x[0])  # 旧 → 新
    first_days, first_rate = ordered[0]
    last_days, last_rate = ordered[-1]
    span_days = max(1, first_days - last_days)
    return (last_rate - first_rate) / span_days * 30.0


def _attendance_rate(db: Session, student_id: int) -> float:
    rows = db.query(models.Attendance).filter(models.Attendance.student_id == student_id).all()
    if not rows:
        return 0.0
    ok = sum(1 for a in rows if a.status in ("present", "late"))
    return round(ok / len(rows) * 100, 1)


def _weighted_total(weights: dict, rates: dict) -> tuple[float, float]:
    """按权重计算加权总分；返回 (总分, 已覆盖权重)。"""
    total = 0.0
    covered = 0.0
    for name, weight in weights.items():
        if name in rates:
            total += weight * rates[name] / 100.0
            covered += weight
    return total, covered


def _rank_hint(exam_type: str, region: str, projected: float, lines) -> str:
    """基于分数线的粗略位次提示（估算，仅供参考）。"""
    if exam_type == "zhongkao":
        if projected >= 690:
            return "参考估算：约六区前 2%"
        if projected >= 665:
            return "参考估算：约六区前 8%"
        if projected >= 627:
            return "参考估算：约六区前 20%"
        if projected >= 598:
            return "参考估算：约六区前 30%"
        if projected >= 510:
            return "参考估算：约六区前 60%"
        return "参考估算：六区后 40%，需重点提升"
    # 高考
    if projected >= 640:
        return "参考估算：可冲击省内顶尖 985"
    if projected >= 610:
        return "参考估算：可冲击 211/双一流"
    if projected >= 532:
        return "参考估算：特招线上，具备 211 冲刺基础"
    if projected >= 484:
        return "参考估算：本科线上，可冲击公办本科"
    return "参考估算：接近本科线，需全力冲刺"


def _build_roadmap(db: Session, student: models.Student) -> schemas.RoadmapOut:
    latest, trend = _student_school_rates(db, student.id)
    if not latest:
        return schemas.RoadmapOut(
            student=schemas.StudentOut.model_validate(student),
            stage=schemas.RoadmapStage(stage="暂无数据"),
            summary="该学生暂无学校考试成绩，无法进行择校冲刺分析。请先录入学校考试成绩。",
        )

    stage_name, exam_type, region = STAGE_META.get(student.grade, ("暂无数据", "zhongkao", "苏州"))
    today = date.today()
    subject_names = {sid: _subject_name(db, sid) for sid in latest}
    rates = {subject_names[sid]: r[1] for sid, r in latest.items()}
    att_rate = _attendance_rate(db, student.id)
    track = getattr(student, "track", "") or ""

    current_total = 0.0
    total_full = 0.0

    if exam_type == "zhongkao":
        # 中考：语数英物化政史 + 体育；地理/生物为会考科目不计分
        zk_weights = ZHONGKAO_WEIGHTS
        total, covered = _weighted_total(zk_weights, rates)
        tiyu = round(TIYU_BASE + att_rate / 100.0 * 6.0, 1)
        current_total = round(total / covered * (ZHONGKAO_FULL - 50) + tiyu, 1) if covered else 0.0
        total_full = ZHONGKAO_FULL
    else:
        if track in TRACK_FIRST:
            track_subjects = {"语文", "数学", "英语"} | (
                TRACK_SUBJECTS_NAME.get(track, set())
            )
            total, covered = _weighted_total(
                {k: v for k, v in GAOKAO_WEIGHTS.items() if k in track_subjects}, rates
            )
            current_total = round(total / covered * GAOKAO_FULL, 1) if covered else 0.0
            total_full = GAOKAO_FULL
        else:
            # 高一未分科：分别估算文理
            wen = {k: v for k, v in GAOKAO_WEIGHTS.items() if k in {"语文", "数学", "英语", "政治", "历史", "地理"}}
            li = {k: v for k, v in GAOKAO_WEIGHTS.items() if k in {"语文", "数学", "英语", "物理", "化学", "生物"}}
            t_wen, c_wen = _weighted_total(wen, rates)
            t_li, c_li = _weighted_total(li, rates)
            t_wen = t_wen / c_wen * GAOKAO_FULL if c_wen else 0.0
            t_li = t_li / c_li * GAOKAO_FULL if c_li else 0.0
            current_total = round(max(t_wen, t_li), 1)
            total_full = GAOKAO_FULL

    # 趋势推算（每月 pp 变化 → 到考试的参考提升）
    slopes = []
    for sid, pts in trend.items():
        slopes.append(_trend_slope_pp(pts))
    avg_slope = sum(slopes) / len(slopes) if slopes else 0.0
    months = _months_to_exam(today, exam_type)
    cap = 30 if stage_name in ("中考冲刺期", "高考冲刺期") else 18
    uplift = _clamp(avg_slope * min(months, 6) * 0.45, -cap, cap)
    projected_total = _round1(current_total + uplift)

    # 分数线
    line_q = db.query(models.AdmissionLine).filter(
        models.AdmissionLine.exam_type == exam_type,
        models.AdmissionLine.region == region,
    )
    lines = line_q.order_by(models.AdmissionLine.year.desc(), models.AdmissionLine.score.desc()).all()
    if exam_type == "gaokao" and track in TRACK_FIRST:
        track_label = "历史类" if track == "文科" else "物理类"
        lines = [ln for ln in lines if not ln.track or ln.track == track_label]
    rank_hint = _rank_hint(exam_type, region, projected_total, lines)

    # 分数线对照：只列出控制线 + 与学生分数最接近的学校（够得着/有参考意义）
    control_categories = ("控制线", "本科线", "特殊类型招生控制线", "专科线")
    line_items = []
    seen_control = set()
    for ln in lines:
        if ln.category not in control_categories:
            continue
        key = (ln.school, ln.category, ln.track)
        if key in seen_control:
            continue
        seen_control.add(key)
        gap = round(projected_total - ln.score, 1)
        line_items.append(schemas.RoadmapLineItem(
            line_id=ln.id, school=ln.school, category=ln.category,
            track=ln.track, province=ln.province or "", score=ln.score,
            gap=gap, status="稳上" if gap >= 8 else ("冲刺" if gap >= -12 else "差距"),
        ))
    school_items = []
    seen_school = set()
    for ln in lines:
        if ln.category in control_categories:
            continue
        key = (ln.school, ln.category, ln.track)
        if key in seen_school:
            continue
        seen_school.add(key)
        gap = projected_total - ln.score
        if gap < -60:
            continue  # 明显够不到的高分学校不进入对照，避免无效信息
        school_items.append(schemas.RoadmapLineItem(
            line_id=ln.id, school=ln.school, category=ln.category,
            track=ln.track, province=ln.province or "", score=ln.score,
            gap=round(gap, 1),
            status="稳上" if gap >= 8 else ("冲刺" if gap >= -12 else "差距"),
        ))
    school_items.sort(key=lambda x: (abs(x.gap), 0 if x.province == "江苏" else 1))
    line_items = line_items + school_items[:12]

    # 目标学校：全库按分差就近匹配，冲刺/稳妥/差距三档，分数接近时江苏院校优先
    targets = []
    for ln in lines:
        gap = projected_total - ln.score
        targets.append(schemas.RoadmapTarget(
            school=ln.school, category=ln.category, track=ln.track,
            province=ln.province or "",
            line_score=ln.score, projected_score=projected_total,
            gap=round(gap, 1),
            status="稳妥" if gap >= 8 else ("冲刺" if gap >= -12 else "差距"),
        ))

    def _near_key(t):
        # 分差接近时（按 1 分桶）江苏院校优先
        return (0 if t.province == "江苏" else 1, round(-t.gap, 0))

    sprint = sorted([t for t in targets if t.status == "冲刺"], key=_near_key)
    safe = sorted(
        [t for t in targets if t.status == "稳妥"],
        key=lambda t: (0 if t.province == "江苏" else 1, round(t.gap, 0)),
    )
    far = [t for t in targets if t.status == "差距" and t.gap >= -60]
    far.sort(key=_near_key)
    top_targets = sprint[:4] + safe[:3] + far[:3]
    seen_targets = set()
    dedup_targets = []
    for t in top_targets:
        if t.school not in seen_targets:
            seen_targets.add(t.school)
            dedup_targets.append(t)

    # 分科洞察
    subject_insights = []
    for sid, (days_ago, rate, rec) in latest.items():
        name = subject_names[sid]
        if exam_type == "zhongkao" and name in ("地理", "生物"):
            weight = 0.0
            note_extra = "会考科目，不计入中考总分"
        else:
            weight = (ZHONGKAO_WEIGHTS if exam_type == "zhongkao" else GAOKAO_WEIGHTS).get(name, 0.0)
            note_extra = ""
        pts = trend.get(sid, [])
        slope = _trend_slope_pp(pts)
        avg = round(sum(p[1] for p in pts) / len(pts), 1) if pts else rate
        target_rate = min(88.0, rate + 12.0)
        gain = round(max(0.0, (target_rate - rate) / 100.0 * weight), 1) if weight else 0.0
        level = "优势" if rate >= 80 else ("中等" if rate >= 60 else "薄弱")
        advice = _subject_advice(name, level, rate, slope, gain, att_rate, weight, note_extra)
        subject_insights.append(schemas.RoadmapSubjectInsight(
            subject_id=sid, subject=name,
            avg_rate=avg, latest_rate=rate,
            trend_delta=_round1(slope * 1.5),
            weight=weight, gain_potential=gain, level=level, advice=advice,
        ))
    subject_insights.sort(key=lambda x: -x.gain_potential)

    suggestions = _stage_suggestions(
        stage_name, exam_type, student.grade, track, projected_total,
        current_total, total_full, subject_insights[:3], top_targets,
    )
    summary = _stage_summary(
        student, stage_name, exam_type, track, current_total, projected_total,
        total_full, top_targets, att_rate, rank_hint=rank_hint,
    )

    return schemas.RoadmapOut(
        student=schemas.StudentOut.model_validate(student),
        stage=schemas.RoadmapStage(
            stage=stage_name, exam_type=exam_type, region=region,
            current_total=_round1(current_total), projected_total=projected_total,
            total_full=total_full, rank_hint=rank_hint,
        ),
        lines=line_items,
        targets=dedup_targets,
        subjects=subject_insights,
        suggestions=suggestions,
        summary=summary,
    )


TRACK_SUBJECTS_NAME = {
    "文科": {"政治", "历史", "地理"},
    "理科": {"物理", "化学", "生物"},
}


def _subject_advice(name, level, rate, slope, gain, att_rate, weight, note_extra) -> str:
    parts = []
    if note_extra:
        parts.append(note_extra)
    if level == "薄弱":
        parts.append(f"当前得分率 {rate:.0f}%，为明显短板" + (f"，提分空间约 {gain:.0f} 分" if gain > 0 else ""))
        if slope < -1:
            parts.append("近期仍在下滑，需尽快止损")
        elif slope < 1:
            parts.append("近期提升不明显，需调整学习方法")
    elif level == "中等":
        parts.append(f"得分率 {rate:.0f}%，处于中等水平" + (f"，还有约 {gain:.0f} 分可挖" if gain > 0 else ""))
        if slope >= 2:
            parts.append("保持当前节奏，继续巩固")
    else:
        parts.append(f"得分率 {rate:.0f}%，属于优势科目，建议保持并适度拔高")
    if att_rate < 85:
        parts.append("注意：出勤率偏低会影响补习效果，建议先保证出勤")
    return "，".join(parts) or "保持稳定"


def _stage_suggestions(stage, exam_type, grade, track, projected, current, full, weak_subjects, targets) -> list[str]:
    s = []
    target_line = f"目前估算 {projected:.0f}/{full:.0f} 分"
    if stage == "初中基础期":
        s.append(f"{target_line}，目标可对标苏州四星级高中（约 598-690 分）与普高线（约 510 分）")
        s.append("初一初二以语数英打底为主，数学重在计算与逻辑，英语重在词汇与语感，建议每天固定 30-60 分钟")
        s.append("政史地生注重课堂积累与错题整理，避免考前突击")
        s.append("坚持补习出勤并按时完成作业，为初三冲刺建立节奏")
    elif stage == "中考冲刺期":
        s.append(f"{target_line}，距离中考约 10 个月，按当前补习节奏预计可达 {projected:.0f} 分")
        if targets:
            sprint_names = "、".join(t.school for t in targets[:3] if t.status == "冲刺") or "（暂无稳妥冲刺目标）"
            safe_names = "、".join(t.school for t in targets if t.status == "稳妥")[:40]
            s.append(f"建议冲刺：{sprint_names}" + (f"；保底参考：{safe_names}" if safe_names else ""))
        if weak_subjects:
            names = "、".join(x.subject for x in weak_subjects)
            s.append(f"重点提分科目：{names}，按“基础→专项→真题”顺序推进")
        s.append("每周安排 1 套真题限时训练，统计错题类型并回补知识点")
        s.append("体育计入总分，建议同步锻炼，争取满分区间")
    elif stage == "高中基础期":
        s.append(f"{target_line}，高一阶段重点在于打好语数英基础并初步确定选科方向")
        if track:
            s.append(f"当前登记选科方向：{track}，可参考目标大学专业对选科的要求")
        else:
            s.append("建议根据各科得分率与兴趣确定选科：文科方向参考政史地表现，理科方向参考物化生表现")
        s.append("语数英占高考 450 分，务必优先稳固；选科科目保持均衡发展，避免过早偏废")
        s.append("可提前查阅江苏高考本科线（历史类 484/物理类 456）与目标院校投档线，树立分数目标")
    elif stage == "高中提升期":
        s.append(f"{target_line}，高二应锁定方向并开始攻坚弱科")
        s.append(f"当前方向：{track or '未分科'}；建议明确目标大学层次（特招线历史类 532/物理类 513）")
        if weak_subjects:
            names = "、".join(x.subject for x in weak_subjects)
            s.append(f"主攻：{names}，每周安排专题训练并复盘错题")
        s.append("保持补习出勤与课后作业质量，成绩提升是缓慢积累的过程，忌急于求成")
    else:  # 高考冲刺期
        s.append(f"{target_line}，距离高考约 10 个月，当前估算位于{_rank_hint_short(projected)}")
        if targets:
            sprint_names = "、".join(t.school for t in targets[:3] if t.status == "冲刺") or "（暂无稳妥冲刺目标）"
            safe_names = "、".join(t.school for t in targets if t.status == "稳妥")[:40]
            s.append(f"建议冲刺：{sprint_names}" + (f"；保底参考：{safe_names}" if safe_names else ""))
        if weak_subjects:
            names = "、".join(x.subject for x in weak_subjects)
            s.append(f"重点提分科目：{names}，按“知识漏洞→专题强化→模拟卷”推进")
        s.append("每两周一次全真模拟，记录时间分配与失分点，动态调整复习计划")
        s.append("稳定心态，保障睡眠与锻炼，避免考前疲劳")
    return s


def _rank_hint_short(projected: float) -> str:
    if projected >= 640:
        return "顶尖 985 冲刺区间"
    if projected >= 610:
        return "211/双一流冲刺区间"
    if projected >= 532:
        return "特招线上方"
    if projected >= 484:
        return "本科线上方"
    return "本科线附近"


def _stage_summary(student, stage, exam_type, track, current, projected, full, targets, att_rate, rank_hint) -> str:
    track_txt = f"，{track}" if track else ""
    base = (
        f"{student.name}（{student.grade}{track_txt}）当前阶段为“{stage}”。"
        f"按最近学校考试成绩估算，{('中考' if exam_type == 'zhongkao' else '高考')}总分约 {current:.0f}/{full:.0f} 分"
        f"（出勤率 {att_rate}%）；若保持当前补习与学习节奏，预计可达到约 {projected:.0f} 分。"
    )
    if targets:
        sprint = [t for t in targets if t.status == "冲刺"]
        safe = [t for t in targets if t.status == "稳妥"]
        if sprint:
            base += f"可冲刺学校：{'、'.join(t.school for t in sprint[:3])}。"
        if safe:
            base += f"较稳妥选择：{'、'.join(t.school for t in safe[:2])}。"
    if att_rate < 85:
        base += "注意该生出勤率偏低，补习效果可能打折扣，建议先解决出勤问题。"
    return base


# ---------------- API ----------------


@router.get("/admission-lines", response_model=list[schemas.AdmissionLineOut])
def list_admission_lines(
    exam_type: str = None,
    region: str = None,
    year: int = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.AdmissionLine)
    if exam_type:
        q = q.filter(models.AdmissionLine.exam_type == exam_type)
    if region:
        q = q.filter(models.AdmissionLine.region == region)
    if year:
        q = q.filter(models.AdmissionLine.year == year)
    return q.order_by(
        models.AdmissionLine.exam_type,
        models.AdmissionLine.year.desc(),
        models.AdmissionLine.track,
        models.AdmissionLine.score.desc(),
    ).all()


@router.post("/admission-lines", response_model=schemas.AdmissionLineOut)
def create_admission_line(body: schemas.AdmissionLineCreate, db: Session = Depends(get_db)):
    rec = models.AdmissionLine(**body.model_dump())
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


@router.put("/admission-lines/{line_id}", response_model=schemas.AdmissionLineOut)
def update_admission_line(line_id: int, body: schemas.AdmissionLineUpdate, db: Session = Depends(get_db)):
    rec = db.query(models.AdmissionLine).filter(models.AdmissionLine.id == line_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="分数线记录不存在")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(rec, key, value)
    db.commit()
    db.refresh(rec)
    return rec


@router.delete("/admission-lines/{line_id}")
def delete_admission_line(line_id: int, db: Session = Depends(get_db)):
    rec = db.query(models.AdmissionLine).filter(models.AdmissionLine.id == line_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="分数线记录不存在")
    db.delete(rec)
    db.commit()
    return {"ok": True}


@router.get("/roadmap/{student_id}", response_model=schemas.RoadmapOut)
def roadmap(student_id: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return _build_roadmap(db, student)


def _roadmap_prompt(db: Session, roadmap_data: schemas.RoadmapOut) -> str:
    s = roadmap_data.student
    st = roadmap_data.stage
    lines = "\n".join(
        f"- {x.school}（{x.category}{('/' + x.track) if x.track else ''}{('/' + x.province) if x.province == '江苏' else ''}）：{x.score:.0f} 分，"
        f"与学生估算分差 {x.gap:+.0f}（{x.status}）"
        for x in roadmap_data.lines[:14]
    ) or "- 暂无"
    targets = "\n".join(
        f"- {t.school}（{t.category}{('/' + t.track) if t.track else ''}{('/江苏') if t.province == '江苏' else ''}）：{t.line_score:.0f} 分，"
        f"分差 {t.gap:+.0f} → {t.status}"
        for t in roadmap_data.targets[:8]
    ) or "- 暂无"
    subjects = "\n".join(
        f"- {x.subject}：平均得分率 {x.avg_rate}%，最新 {x.latest_rate}%，"
        f"权重 {x.weight:.0f} 分，提分空间约 {x.gain_potential:.0f} 分，{x.level}；{x.advice}"
        for x in roadmap_data.subjects[:8]
    ) or "- 暂无"
    suggestions = "\n".join(f"- {x}" for x in roadmap_data.suggestions) or "- 暂无"
    return f"""请根据以下择校冲刺分析数据，为这名学生生成一份中文“升学择校冲刺报告”。

【硬性要求】
1. 只允许使用下方数据，禁止编造分数线、学校或百分比。
2. 固定输出 Markdown 章节：
# {s.name}升学择校冲刺报告
## 一、当前定位
## 二、目标学校分析
## 三、分科提分空间
## 四、冲刺策略
## 五、学习与心态建议
3. 每条结论必须引用具体分数，禁止空泛套话。目标学校三档含义：
   - 冲刺：学校投档线略高于或接近学生估算分（分差约 -12 ~ +8），需要冲一冲；
   - 稳妥：学校投档线明显低于学生估算分（分差 ≥ +8），录取把握大；
   - 差距：学校投档线明显高于学生估算分（分差 < -12），只作为远期目标，绝不能写成“保底”。
   同一分数区间优先推荐江苏院校。
4. 全文 600-900 字，第三人称，语言专业、可落地。

学生：{s.name}，{s.grade}，{s.track or '文理未分'}，出勤表现见数据。
当前阶段：{st.stage}（{'中考' if st.exam_type == 'zhongkao' else '高考'}，{st.region}）
成绩估算：当前 {st.current_total:.0f}/{st.total_full:.0f} 分，预计可达 {st.projected_total:.0f} 分
{st.rank_hint}

【规则引擎总评】
{roadmap_data.summary}

【分数线对照（仅列出与学生分数最接近的学校，未列出的高分学校无需提及）】
{lines}

【推荐目标学校】
{targets}

【分科洞察】
{subjects}

【学习建议】
{suggestions}
"""


def _call_deepseek(api_key: str, base_url: str, model: str, prompt: str) -> tuple[str, str]:
    url = base_url.rstrip("/") + "/chat/completions"
    candidates = [model] if model == "deepseek-chat" else [model, "deepseek-chat"]
    for candidate in candidates:
        payload = json.dumps({
            "model": candidate,
            "messages": [
                {"role": "system", "content": "你是课外辅导机构的升学规划数据分析助手。只能使用用户提供的数据撰写报告，不得编造分数线、学校或百分比，必须使用固定 Markdown 章节，每个结论要有数字支撑。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.25,
            "max_tokens": 2200,
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
    raise HTTPException(status_code=502, detail="DeepSeek 连续返回空报告，请检查 API Key 与模型配置")


def _get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(models.AppSetting).filter(models.AppSetting.key == key).first()
    return row.value if row and row.value else default


@router.post("/ai-roadmap", response_model=schemas.AiInsightOut)
def ai_roadmap(body: schemas.AiRoadmapRequest, db: Session = Depends(get_db)):
    roadmap_data = _build_roadmap(db, db.query(models.Student).filter(models.Student.id == body.student_id).first())
    api_key = body.api_key or os.environ.get("DEEPSEEK_API_KEY") or _get_setting(db, "deepseek_api_key")
    model = body.model or _get_setting(db, "deepseek_model", "deepseek-chat")
    base_url = _get_setting(db, "deepseek_base_url", "https://api.deepseek.com")

    if not api_key:
        # 无 AI Key 时返回规则引擎版本，保证功能可用
        fallback = f"# {roadmap_data.student.name}升学择校冲刺报告（规则引擎版）\n\n## 一、当前定位\n\n{roadmap_data.summary}\n\n## 二、目标学校分析\n\n" + "\n".join(
            f"- {t.school}（{t.category}）：线 {t.line_score:.0f} 分，分差 {t.gap:+.0f} → {t.status}"
            for t in roadmap_data.targets[:8]
        ) + "\n\n## 三、分科提分空间\n\n" + "\n".join(
            f"- {x.subject}：{x.level}，最新得分率 {x.latest_rate}%，提分空间约 {x.gain_potential:.0f} 分"
            for x in roadmap_data.subjects[:6]
        ) + "\n\n## 四、冲刺策略与学习建议\n\n" + "\n".join(
            f"- {s}" for s in roadmap_data.suggestions
        ) + "\n\n（提示：配置 DeepSeek API Key 后可生成更详细的 AI 版冲刺报告。）"
        return schemas.AiInsightOut(
            answer=fallback,
            model="rule-engine",
            generated_at=datetime.now().isoformat(timespec="seconds"),
        )

    prompt = _roadmap_prompt(db, roadmap_data)
    try:
        answer, used_model = _call_deepseek(api_key, base_url, model, prompt)
    except HTTPException as e:
        # AI 服务不可用/超时时降级为规则引擎报告，保证功能可用
        fallback = (
            f"# {roadmap_data.student.name}升学择校冲刺报告（规则引擎版）\n\n"
            f"## 一、当前定位\n\n{roadmap_data.summary}\n\n"
            f"## 二、目标学校分析\n\n" + "\n".join(
                f"- {t.school}（{t.category}）：线 {t.line_score:.0f} 分，分差 {t.gap:+.0f} → {t.status}"
                for t in roadmap_data.targets[:8]
            ) + "\n\n## 三、分科提分空间\n\n" + "\n".join(
                f"- {x.subject}：{x.level}，最新得分率 {x.latest_rate}%，提分空间约 {x.gain_potential:.0f} 分"
                for x in roadmap_data.subjects[:6]
            ) + "\n\n## 四、冲刺策略与学习建议\n\n" + "\n".join(
                f"- {s}" for s in roadmap_data.suggestions
            ) + f"\n\n（AI 服务暂时不可用：{e.detail}，本次由规则引擎生成。）"
        )
        return schemas.AiInsightOut(
            answer=fallback,
            model="rule-engine",
            generated_at=datetime.now().isoformat(timespec="seconds"),
        )
    return schemas.AiInsightOut(
        answer=answer,
        model=used_model,
        generated_at=datetime.now().isoformat(timespec="seconds"),
    )
