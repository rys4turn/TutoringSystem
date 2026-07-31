from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class RoomCreate(BaseModel):
    name: str; room_type: str; capacity: int; notes: str = ""

class RoomOut(BaseModel):
    id: int; name: str; room_type: str; capacity: int; notes: str
    model_config = {"from_attributes": True}


class StudentCreate(BaseModel):
    name: str; grade_level: str; grade: str; phone: str = ""; notes: str = ""

class StudentOut(BaseModel):
    id: int; name: str; grade_level: str; grade: str; phone: str; notes: str
    model_config = {"from_attributes": True}


class SubjectCreate(BaseModel):
    name: str

class SubjectOut(BaseModel):
    id: int; name: str
    model_config = {"from_attributes": True}


class TeacherCreate(BaseModel):
    name: str; phone: str = ""; notes: str = ""; subject_ids: list[int] = []

class TeacherOut(BaseModel):
    id: int; name: str; phone: str; notes: str; subjects: list[SubjectOut] = []
    model_config = {"from_attributes": True}


class CourseCreate(BaseModel):
    name: str; subject_id: int; teacher_id: int; room_id: int
    day_of_week: int; time_slot: int; course_type: str = "class"
    max_students: int = 8; notes: str = ""; student_ids: list[int] = []

class CourseOut(BaseModel):
    id: int; name: str; subject_id: int; teacher_id: int; room_id: int
    day_of_week: int; time_slot: int; course_type: str; max_students: int; notes: str
    subject: Optional[SubjectOut] = None
    teacher: Optional[TeacherOut] = None
    room: Optional[RoomOut] = None
    students: list[StudentOut] = []
    student_count: int = 0
    model_config = {"from_attributes": True}

class CourseUpdate(BaseModel):
    name: Optional[str] = None; subject_id: Optional[int] = None
    teacher_id: Optional[int] = None; room_id: Optional[int] = None
    day_of_week: Optional[int] = None; time_slot: Optional[int] = None
    course_type: Optional[str] = None; max_students: Optional[int] = None
    notes: Optional[str] = None; student_ids: Optional[list[int]] = None


# Attendance
class AttendanceCreate(BaseModel):
    course_id: int; student_id: int; date_val: date; status: str = "present"; notes: str = ""

class AttendanceOut(BaseModel):
    id: int; course_id: int; student_id: int
    date_val: date = Field(validation_alias="date")
    status: str; notes: str
    student: Optional[StudentOut] = None
    model_config = {"from_attributes": True}

class AttendanceBatch(BaseModel):
    course_id: int; date_val: date; records: list[dict]


class AttendanceReportItem(BaseModel):
    student: StudentOut; records: list[AttendanceOut] = []
    present_count: int = 0; absent_count: int = 0


# Schedule Adjustment
class AdjustmentCreate(BaseModel):
    course_id: int; adjustment_date: date
    original_day: int; original_slot: int; original_room_id: int
    new_day: Optional[int] = None; new_slot: Optional[int] = None
    new_room_id: Optional[int] = None
    adjustment_type: str = "rescheduled"; reason: str = ""

class AdjustmentOut(BaseModel):
    id: int; course_id: int; adjustment_date: date
    original_day: int; original_slot: int; original_room_id: int
    new_day: Optional[int] = None; new_slot: Optional[int] = None
    new_room_id: Optional[int] = None
    adjustment_type: str; reason: str
    course: Optional[CourseOut] = None
    model_config = {"from_attributes": True}
