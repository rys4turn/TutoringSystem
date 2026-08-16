from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class RoomCreate(BaseModel):
    name: str; room_type: str; capacity: int; notes: str = ""

class RoomOut(BaseModel):
    id: int; name: str; room_type: str; capacity: int; notes: str
    model_config = {"from_attributes": True}


class StudentCreate(BaseModel):
    name: str; grade_level: str; grade: str; track: str = ""; phone: str = ""; notes: str = ""

class StudentOut(BaseModel):
    id: int; name: str; grade_level: str; grade: str; track: str; phone: str; notes: str
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


# Score Records
EXAM_TYPES = ["school_exam", "quiz", "entry_test"]

class ScoreRecordCreate(BaseModel):
    student_id: int
    subject_id: int
    course_id: Optional[int] = None
    exam_type: str = "quiz"
    exam_name: str
    score: float
    max_score: float = 100
    exam_date: date
    notes: str = ""

class ScoreRecordUpdate(BaseModel):
    student_id: Optional[int] = None
    subject_id: Optional[int] = None
    course_id: Optional[int] = None
    exam_type: Optional[str] = None
    exam_name: Optional[str] = None
    score: Optional[float] = None
    max_score: Optional[float] = None
    exam_date: Optional[date] = None
    notes: Optional[str] = None

class ScoreRecordOut(BaseModel):
    id: int
    student_id: int
    subject_id: int
    course_id: Optional[int] = None
    exam_type: str
    exam_name: str
    score: float
    max_score: float
    exam_date: date
    notes: str
    rate: float = 0.0
    student: Optional[StudentOut] = None
    subject: Optional[SubjectOut] = None
    course: Optional[CourseOut] = None
    model_config = {"from_attributes": True}


# Attendance analysis
class AttendanceSummary(BaseModel):
    total: int = 0
    present: int = 0
    late: int = 0
    absent: int = 0
    leave: int = 0
    rate: float = 0.0

class StudentAttendanceStat(BaseModel):
    student: StudentOut
    total: int = 0
    present: int = 0
    late: int = 0
    absent: int = 0
    leave: int = 0
    rate: float = 0.0

class SubjectAttendanceStat(BaseModel):
    subject_id: int
    subject: SubjectOut
    total: int = 0
    present: int = 0
    late: int = 0
    absent: int = 0
    leave: int = 0
    rate: float = 0.0

class AttendanceTrendPoint(BaseModel):
    date_val: date
    total: int = 0
    present: int = 0
    late: int = 0
    rate: float = 0.0

class AttendanceAnalysisOut(BaseModel):
    summary: AttendanceSummary
    by_student: list[StudentAttendanceStat] = []
    by_subject: list[SubjectAttendanceStat] = []
    trend: list[AttendanceTrendPoint] = []


# Score analysis
class ScoreSummary(BaseModel):
    total: int = 0
    school_count: int = 0
    quiz_count: int = 0
    entry_count: int = 0
    avg_score: float = 0.0
    avg_rate: float = 0.0
    best_rate: float = 0.0
    lowest_rate: float = 0.0

class SubjectScoreStat(BaseModel):
    subject_id: int
    subject: SubjectOut
    total: int = 0
    school_count: int = 0
    quiz_count: int = 0
    entry_count: int = 0
    avg_score: float = 0.0
    avg_rate: float = 0.0
    best_rate: float = 0.0
    lowest_rate: float = 0.0

class StudentScoreStat(BaseModel):
    student: StudentOut
    total: int = 0
    avg_score: float = 0.0
    avg_rate: float = 0.0
    school_avg_rate: float = 0.0
    quiz_avg_rate: float = 0.0
    entry_avg_rate: float = 0.0
    best_rate: float = 0.0
    lowest_rate: float = 0.0

class ScoreTrendPoint(BaseModel):
    id: int
    exam_date: date
    exam_name: str
    exam_type: str
    subject_id: int
    subject: SubjectOut
    score: float
    max_score: float
    rate: float

class ScoreAnalysisOut(BaseModel):
    summary: ScoreSummary
    by_subject: list[SubjectScoreStat] = []
    by_student: list[StudentScoreStat] = []
    trend: list[ScoreTrendPoint] = []


# Radar chart
class RadarAxis(BaseModel):
    subject_id: int
    subject: str
    record_count: int = 0
    school_avg_rate: float = 0.0
    quiz_avg_rate: float = 0.0
    entry_avg_rate: float = 0.0
    overall_avg_rate: float = 0.0
    attendance_rate: float = 0.0

class RadarOut(BaseModel):
    student: StudentOut
    axes: list[RadarAxis] = []


# App settings / DeepSeek
class SettingsOut(BaseModel):
    deepseek_api_key_set: bool = False
    deepseek_api_key_masked: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"

class SettingsUpdate(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None

class AiReportRequest(BaseModel):
    student_id: int
    api_key: Optional[str] = None
    model: Optional[str] = None

class AiReportOut(BaseModel):
    student_id: int
    report: str = ""
    model: str = ""
    generated_at: str = ""


# Dashboard / AI insight
class DashboardCounts(BaseModel):
    students: int = 0
    teachers: int = 0
    courses: int = 0
    subjects: int = 0
    rooms: int = 0

class TodayAttendanceOut(BaseModel):
    total: int = 0
    present: int = 0
    late: int = 0
    absent: int = 0
    leave: int = 0

class SubjectMetricOut(BaseModel):
    subject_id: int
    subject: str
    course_count: int = 0
    student_count: int = 0
    attendance_rate: float = 0.0
    score_rate: float = 0.0

class ScoreTrendPointOut(BaseModel):
    date_val: str
    avg_rate: float = 0.0
    count: int = 0

class RoomOccupancyOut(BaseModel):
    room_id: int
    room_name: str
    room_type: str = ""
    today_courses: int = 0
    today_students: int = 0

class DashboardOut(BaseModel):
    counts: DashboardCounts = DashboardCounts()
    today_date: str = ""
    today_dow: int = 0
    today_courses: list[CourseOut] = []
    today_student_seats: int = 0
    today_attendance: TodayAttendanceOut = TodayAttendanceOut()
    weekly_load: list[int] = []
    slot_load: list[int] = []
    room_occupancy: list[RoomOccupancyOut] = []
    attendance: AttendanceSummary = AttendanceSummary()
    scores: ScoreSummary = ScoreSummary()
    subject_metrics: list[SubjectMetricOut] = []
    attendance_trend: list[AttendanceTrendPoint] = []
    score_trend: list[ScoreTrendPointOut] = []
    adjustments: list[AdjustmentOut] = []

class CourseHealthOut(BaseModel):
    course_id: int
    name: str
    subject: str
    teacher: str
    room: str
    day: int
    slot: int
    students: int = 0
    max_students: int = 0
    attendance_rate: float = 0.0
    score_rate: float = 0.0
    utilization: float = 0.0
    health_score: float = 0.0
    risk_level: str = "low"
    signals: list[str] = []
    trend_delta: float = 0.0
    teacher_load: int = 0

class RiskStudentOut(BaseModel):
    student_id: int
    name: str
    grade: str
    grade_level: str = ""
    attendance_rate: float = 0.0
    score_rate: float = 0.0
    trend_delta: float = 0.0
    recent_absences: int = 0
    courses: int = 0
    risk_score: float = 0.0
    risk_level: str = "low"
    signals: list[str] = []

class AiInsightRequest(BaseModel):
    insight_type: str = "overview"
    question: str = ""
    history: list[dict] = []
    api_key: Optional[str] = None
    model: Optional[str] = None

class AiInsightOut(BaseModel):
    answer: str = ""
    model: str = ""
    generated_at: str = ""


# 录取分数线（中考/高考）
EXAM_TYPE_LABELS = {"zhongkao": "中考", "gaokao": "高考"}

class AdmissionLineOut(BaseModel):
    id: int
    exam_type: str
    region: str
    year: int
    category: str
    track: str = ""
    province: str = ""
    school: str
    code: str = ""
    score: float
    note: str = ""
    model_config = {"from_attributes": True}

class AdmissionLineCreate(BaseModel):
    exam_type: str = "zhongkao"
    region: str = "苏州"
    year: int = 2026
    category: str = "四星级高中"
    track: str = ""
    province: str = ""
    school: str
    code: str = ""
    score: float
    note: str = ""

class AdmissionLineUpdate(BaseModel):
    exam_type: Optional[str] = None
    region: Optional[str] = None
    year: Optional[int] = None
    category: Optional[str] = None
    track: Optional[str] = None
    province: Optional[str] = None
    school: Optional[str] = None
    code: Optional[str] = None
    score: Optional[float] = None
    note: Optional[str] = None


# 择校冲刺分析
class RoadmapLineItem(BaseModel):
    line_id: int = 0
    school: str
    category: str
    track: str = ""
    province: str = ""
    score: float
    gap: float
    status: str = "冲刺"  # 稳上/冲刺/差距

class RoadmapTarget(BaseModel):
    school: str
    category: str
    track: str = ""
    province: str = ""
    line_score: float
    projected_score: float
    gap: float
    status: str = "冲刺"  # 冲刺/稳妥/保底

class RoadmapSubjectInsight(BaseModel):
    subject_id: int
    subject: str
    avg_rate: float = 0.0
    latest_rate: float = 0.0
    trend_delta: float = 0.0
    weight: float = 0.0
    gain_potential: float = 0.0
    level: str = "中等"   # 优势/中等/薄弱
    advice: str = ""

class RoadmapStage(BaseModel):
    stage: str = ""          # 初中基础期/中考冲刺期/高中基础期/高考冲刺期
    exam_type: str = ""      # zhongkao/gaokao
    region: str = ""
    current_total: float = 0.0
    projected_total: float = 0.0
    total_full: float = 0.0
    rank_hint: str = ""

class RoadmapOut(BaseModel):
    student: StudentOut
    stage: RoadmapStage
    lines: list[RoadmapLineItem] = []
    targets: list[RoadmapTarget] = []
    subjects: list[RoadmapSubjectInsight] = []
    suggestions: list[str] = []
    summary: str = ""

class AiRoadmapRequest(BaseModel):
    student_id: int
    api_key: Optional[str] = None
    model: Optional[str] = None
