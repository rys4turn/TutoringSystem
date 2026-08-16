from sqlalchemy import Column, Integer, String, ForeignKey, Table, UniqueConstraint, Date, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy import Float
from sqlalchemy import Text
from sqlalchemy.sql import func
from .database import Base

teacher_subject = Table(
    "teacher_subject", Base.metadata,
    Column("teacher_id", Integer, ForeignKey("teachers.id"), primary_key=True),
    Column("subject_id", Integer, ForeignKey("subjects.id"), primary_key=True),
)
enrollment = Table(
    "enrollment", Base.metadata,
    Column("student_id", Integer, ForeignKey("students.id"), primary_key=True),
    Column("course_id", Integer, ForeignKey("courses.id"), primary_key=True),
)

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    room_type = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)
    notes = Column(String, default="")
    courses = relationship("Course", back_populates="room")

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    grade_level = Column(String, nullable=False)
    grade = Column(String, nullable=False)
    track = Column(String, default="")
    phone = Column(String, default="")
    notes = Column(String, default="")
    courses = relationship("Course", secondary=enrollment, back_populates="students")
    attendances = relationship("Attendance", back_populates="student")
    scores = relationship("ScoreRecord", back_populates="student")

class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    teachers = relationship("Teacher", secondary=teacher_subject, back_populates="subjects")
    courses = relationship("Course", back_populates="subject")
    scores = relationship("ScoreRecord", back_populates="subject")

class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, default="")
    notes = Column(String, default="")
    subjects = relationship("Subject", secondary=teacher_subject, back_populates="teachers")
    courses = relationship("Course", back_populates="teacher")

class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("room_id", "day_of_week", "time_slot", name="uq_room_schedule"),)
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)
    time_slot = Column(Integer, nullable=False)
    course_type = Column(String, nullable=False, default="class")
    max_students = Column(Integer, default=8)
    notes = Column(String, default="")
    subject = relationship("Subject", back_populates="courses")
    teacher = relationship("Teacher", back_populates="courses")
    room = relationship("Room", back_populates="courses")
    students = relationship("Student", secondary=enrollment, back_populates="courses")
    attendances = relationship("Attendance", back_populates="course")
    adjustments = relationship("ScheduleAdjustment", back_populates="course")
    scores = relationship("ScoreRecord", back_populates="course")

class Attendance(Base):
    __tablename__ = "attendances"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(String, nullable=False, default="present")
    notes = Column(String, default="")
    created_at = Column(DateTime, server_default=func.now())
    course = relationship("Course", back_populates="attendances")
    student = relationship("Student", back_populates="attendances")

class ScheduleAdjustment(Base):
    __tablename__ = "schedule_adjustments"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    adjustment_date = Column(Date, nullable=False)
    original_day = Column(Integer, nullable=False)
    original_slot = Column(Integer, nullable=False)
    original_room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    new_day = Column(Integer, nullable=True)
    new_slot = Column(Integer, nullable=True)
    new_room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    adjustment_type = Column(String, nullable=False, default="rescheduled")
    reason = Column(String, default="")
    created_at = Column(DateTime, server_default=func.now())
    course = relationship("Course", back_populates="adjustments")
    original_room = relationship("Room", foreign_keys=[original_room_id])
    new_room = relationship("Room", foreign_keys=[new_room_id])

class ScoreRecord(Base):
    __tablename__ = "score_records"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    exam_type = Column(String, nullable=False, default="quiz")
    exam_name = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False, default=100)
    exam_date = Column(Date, nullable=False)
    notes = Column(String, default="")
    created_at = Column(DateTime, server_default=func.now())
    student = relationship("Student", back_populates="scores")
    subject = relationship("Subject", back_populates="scores")
    course = relationship("Course", back_populates="scores")

    @property
    def rate(self) -> float:
        return round(self.score / self.max_score * 100, 1) if self.max_score else 0.0

class AppSetting(Base):
    __tablename__ = "app_settings"
    key = Column(String, primary_key=True)
    value = Column(String, default="")

class AiReport(Base):
    __tablename__ = "ai_reports"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    report = Column(Text, nullable=False)
    model = Column(String, default="")
    generated_at = Column(DateTime, server_default=func.now())
    student = relationship("Student")


class AdmissionLine(Base):
    """中考/高考录取分数线（苏州/江苏），用于学生择校冲刺分析。"""
    __tablename__ = "admission_lines"
    id = Column(Integer, primary_key=True, index=True)
    exam_type = Column(String, nullable=False, default="zhongkao")  # zhongkao | gaokao
    region = Column(String, nullable=False, default="苏州")         # 苏州 | 江苏
    year = Column(Integer, nullable=False, default=2026)
    category = Column(String, nullable=False)   # 批次/类别，如：四星级高中、本科批投档线
    track = Column(String, default="")          # 高考：历史类/物理类；中考为空
    province = Column(String, default="")       # 学校所在省份（江苏院校在分数接近时优先推荐）
    school = Column(String, nullable=False)     # 学校名或控制线名称
    code = Column(String, default="")
    score = Column(Float, nullable=False)       # 录取最低分
    note = Column(String, default="")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    token = Column(String, nullable=True)
    role = Column(String, nullable=False, default="staff")
    created_at = Column(DateTime, server_default=func.now())
