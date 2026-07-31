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
