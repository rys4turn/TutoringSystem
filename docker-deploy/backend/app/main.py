# -*- coding: utf-8 -*-

import os
import sys
import hashlib
from datetime import date

from sqlalchemy import inspect, text
from sqlalchemy.orm import joinedload

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import engine, Base, SessionLocal, get_db
from . import models
from .routers import (
    rooms, students, teachers, subjects, courses, auth,
    attendance, adjustments, scores, analysis, settings, demo, roadmap,
)


def _migrate_schema():
    """轻量迁移：为已有数据库补充新列/新表，避免 create_all 无法追加列的问题。"""
    insp = inspect(engine)
    if "students" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("students")}
        if "track" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE students ADD COLUMN track VARCHAR(20) NOT NULL DEFAULT ''"))
    if "admission_lines" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("admission_lines")}
        if "province" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE admission_lines ADD COLUMN province VARCHAR(30) NOT NULL DEFAULT ''"))


_migrate_schema()
Base.metadata.create_all(bind=engine)


app = FastAPI(title="Tutoring Management System")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(students.router)
app.include_router(teachers.router)
app.include_router(subjects.router)
app.include_router(courses.router)
app.include_router(attendance.router)
app.include_router(adjustments.router)
app.include_router(scores.router)
app.include_router(analysis.router)
app.include_router(roadmap.router)
app.include_router(settings.router)
app.include_router(demo.router)


# -- Explicit attendance report route (before SPA fallback) --
@app.get("/attendance/report", include_in_schema=False)
def _attendance_report(
    student_id: int = None, date_from: date = None, date_to: date = None,
    db=Depends(get_db),
):
    from . import schemas as _s
    q = db.query(models.Attendance).options(
        joinedload(models.Attendance.student),
        joinedload(models.Attendance.course).joinedload(models.Course.subject),
    )
    if student_id:
        q = q.filter(models.Attendance.student_id == student_id)
    if date_from:
        q = q.filter(models.Attendance.date >= date_from)
    if date_to:
        q = q.filter(models.Attendance.date <= date_to)
    attendances = q.order_by(models.Attendance.date.desc()).all()

    result = {}
    for a in attendances:
        sid = a.student_id
        if sid not in result:
            result[sid] = _s.AttendanceReportItem(student=a.student)
        result[sid].records.append(_s.AttendanceOut.model_validate(a))
        if a.status == "present":
            result[sid].present_count += 1
        else:
            result[sid].absent_count += 1
    return list(result.values())


@app.post("/shutdown", include_in_schema=False)
async def shutdown():
    import threading
    in_docker = os.path.exists("/.dockerenv") or os.environ.get("DOCKER_ENV")
    if in_docker:
        return {"ok": True, "docker": True}
    threading.Thread(target=lambda: (__import__("time").sleep(1.0), os._exit(0)), daemon=True).start()
    return {"ok": True}


STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
ASSETS_DIR = os.path.join(STATIC_DIR, "assets")
if os.path.isdir(STATIC_DIR) and os.path.isdir(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

    @app.get("/favicon.svg", include_in_schema=False)
    async def favicon():
        fp = os.path.join(STATIC_DIR, "favicon.svg")
        if os.path.isfile(fp):
            return FileResponse(fp)

    @app.get("/icons.svg", include_in_schema=False)
    async def icons():
        fp = os.path.join(STATIC_DIR, "icons.svg")
        if os.path.isfile(fp):
            return FileResponse(fp)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        ext = os.path.splitext(full_path)[1]
        if ext:
            fp = os.path.join(STATIC_DIR, full_path)
            if os.path.isfile(fp):
                return FileResponse(fp)
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))


def seed():
    db = SessionLocal()
    try:
        if db.query(models.Subject).count() > 0:
            return
        for name in ["语文", "数学", "英语", "物理", "化学", "政治", "历史", "地理", "生物"]:
            db.add(models.Subject(name=name))
        for name, rtype, cap, note in [
            ("1号教室", "large", 8, "大教室，容纳小班课"),
            ("2号教室", "large", 8, "大教室，容纳小班课"),
            ("3号教室", "large", 8, "大教室，容纳小班课"),
            ("4号教室", "small", 2, "小教室，一对一授课/杂物间"),
            ("5号教室", "study", 15, "自习室，学生完成作业"),
        ]:
            db.add(models.Room(name=name, room_type=rtype, capacity=cap, notes=note))
        salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", b"admin123", salt, 100000)
        db.add(models.User(username="admin", password_hash=salt.hex() + ":" + dk.hex(), role="admin"))
        db.commit()
    finally:
        db.close()


def seed_admission_lines():
    from .admission_lines import seed_admission_lines as _seed_lines
    db = SessionLocal()
    try:
        _seed_lines(db)
    finally:
        db.close()


seed()
seed_admission_lines()
