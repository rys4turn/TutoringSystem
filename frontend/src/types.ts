export interface Room {
  id: number;
  name: string;
  room_type: string;
  capacity: number;
  notes: string;
}

export interface Student {
  id: number;
  name: string;
  grade_level: string;
  grade: string;
  phone: string;
  notes: string;
}

export interface Subject {
  id: number;
  name: string;
}

export interface Teacher {
  id: number;
  name: string;
  phone: string;
  notes: string;
  subjects: Subject[];
}

export interface Course {
  id: number;
  name: string;
  subject_id: number;
  teacher_id: number;
  room_id: number;
  day_of_week: number;
  time_slot: number;
  course_type: string;
  max_students: number;
  notes: string;
  subject: Subject | null;
  teacher: Teacher | null;
  room: Room | null;
  students: Student[];
  student_count: number;
}

export interface CourseForm {
  name: string;
  subject_id: number;
  teacher_id: number;
  room_id: number;
  day_of_week: number;
  time_slot: number;
  course_type: string;
  max_students: number;
  notes: string;
  student_ids: number[];
}

export const DAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
export const TIME_SLOTS = ["08:00-10:00", "10:00-12:00", "13:00-15:00", "15:00-17:00", "18:00-20:00"];
export const GRADE_LEVELS = ["初中", "高中"];
export const JUNIOR_GRADES = ["初一", "初二", "初三"];
export const SENIOR_GRADES = ["高一", "高二", "高三"];
export const COURSE_TYPES: Record<string, string> = { class: "课程", self_study: "自习" };
export const ROOM_TYPES: Record<string, string> = { large: "大教室", small: "小教室", study: "自习室" };

export interface User {
  username: string;
  role: string;
}

export interface Attendance {
  id: number;
  course_id: number;
  student_id: number;
  date_val: string;
  status: string;
  notes: string;
  student: Student | null;
}

export interface AttendanceReport {
  student: Student;
  records: Attendance[];
  present_count: number;
  absent_count: number;
}

export interface ScheduleAdjustment {
  id: number;
  course_id: number;
  adjustment_date: string;
  original_day: number;
  original_slot: number;
  original_room_id: number;
  new_day: number | null;
  new_slot: number | null;
  new_room_id: number | null;
  adjustment_type: string;
  reason: string;
  course: Course | null;
}

export interface ScoreRecord {
  id: number;
  student_id: number;
  subject_id: number;
  course_id: number | null;
  exam_type: string;
  exam_name: string;
  score: number;
  max_score: number;
  exam_date: string;
  notes: string;
  rate: number;
  student: Student | null;
  subject: Subject | null;
  course: Course | null;
}

export const EXAM_TYPES: Record<string, string> = { school_exam: "学校考试", quiz: "小测验", entry_test: "入班诊断" };

export interface ScoreForm {
  student_id: number;
  subject_id: number;
  course_id: number | null;
  exam_type: string;
  exam_name: string;
  score: number;
  max_score: number;
  exam_date: string;
  notes: string;
}

export interface AttendanceSummary {
  total: number;
  present: number;
  late: number;
  absent: number;
  leave: number;
  rate: number;
}

export interface StudentAttendanceStat {
  student: Student;
  total: number;
  present: number;
  late: number;
  absent: number;
  leave: number;
  rate: number;
}

export interface SubjectAttendanceStat {
  subject_id: number;
  subject: Subject;
  total: number;
  present: number;
  late: number;
  absent: number;
  leave: number;
  rate: number;
}

export interface AttendanceTrendPoint {
  date_val: string;
  total: number;
  present: number;
  late: number;
  rate: number;
}

export interface AttendanceAnalysis {
  summary: AttendanceSummary;
  by_student: StudentAttendanceStat[];
  by_subject: SubjectAttendanceStat[];
  trend: AttendanceTrendPoint[];
}

export interface ScoreSummary {
  total: number;
  school_count: number;
  quiz_count: number;
  entry_count: number;
  avg_score: number;
  avg_rate: number;
  best_rate: number;
  lowest_rate: number;
}

export interface SubjectScoreStat {
  subject_id: number;
  subject: Subject;
  total: number;
  school_count: number;
  quiz_count: number;
  entry_count: number;
  avg_score: number;
  avg_rate: number;
  best_rate: number;
  lowest_rate: number;
}

export interface StudentScoreStat {
  student: Student;
  total: number;
  avg_score: number;
  avg_rate: number;
  school_avg_rate: number;
  quiz_avg_rate: number;
  best_rate: number;
  lowest_rate: number;
}

export interface ScoreTrendPoint {
  id: number;
  exam_date: string;
  exam_name: string;
  exam_type: string;
  subject_id: number;
  subject: Subject;
  score: number;
  max_score: number;
  rate: number;
}

export interface ScoreAnalysis {
  summary: ScoreSummary;
  by_subject: SubjectScoreStat[];
  by_student: StudentScoreStat[];
  trend: ScoreTrendPoint[];
}

export interface RadarAxis {
  subject_id: number;
  subject: string;
  record_count: number;
  school_avg_rate: number;
  quiz_avg_rate: number;
  entry_avg_rate: number;
  overall_avg_rate: number;
  attendance_rate: number;
}

export interface RadarData {
  student: Student;
  axes: RadarAxis[];
}

export interface SettingsData {
  deepseek_api_key_set: boolean;
  deepseek_api_key_masked: string;
  deepseek_model: string;
  deepseek_base_url: string;
}

export interface AiReport {
  student_id: number;
  report: string;
  model: string;
  generated_at: string;
}
