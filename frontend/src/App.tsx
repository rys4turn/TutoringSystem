import { useState, useEffect, useCallback, type FormEvent } from "react";
import {
  BookOpen, Users, GraduationCap, Calendar, LayoutDashboard, Plus,
  Save, Trash2, X, Edit3, Presentation, Bot,
  AlertTriangle,
  ClipboardCheck, RefreshCw, LogOut, BarChart3, FileText,
} from "lucide-react";
import { api } from "./api";
import { ScoresView, AnalysisView } from "./Analytics";
import { DashboardView } from "./Dashboard";
import { AiLabView } from "./AiLab";
import { Modal } from "./Modal";
import type { Course, Student, Subject, Teacher, ScheduleAdjustment, AttendanceAnalysis } from "./types";
import { DAY_NAMES, TIME_SLOTS, GRADE_LEVELS, JUNIOR_GRADES, SENIOR_GRADES, COURSE_TYPES } from "./types";

const TABS = [
  { id: "dashboard", label: "仪表盘", icon: LayoutDashboard },
  { id: "schedule", label: "排课表", icon: Calendar },
  { id: "students", label: "学生管理", icon: Users },
  { id: "teachers", label: "教师管理", icon: Presentation },
  { id: "courses", label: "课程管理", icon: BookOpen },
  { id: "attendance", label: "考勤管理", icon: ClipboardCheck },
  { id: "adjustments", label: "调课记录", icon: RefreshCw },
  { id: "scores", label: "成绩管理", icon: FileText },
  { id: "analysis", label: "数据分析", icon: BarChart3 },
  { id: "ai-lab", label: "AI 助手", icon: Bot },
] as const;

const COURSE_COLORS = [
  "course-tint-1", "course-tint-2",
  "course-tint-3", "course-tint-4",
  "course-tint-5", "course-tint-6",
  "course-tint-7", "course-tint-8",
  "course-tint-9",
];

function getCourseColor(idx: number) { return COURSE_COLORS[idx % COURSE_COLORS.length]; }

export default function App() {
  const [tab, setTab] = useState("dashboard");
  const [courses, setCourses] = useState<Course[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [error, setError] = useState("");
  const [token, setToken] = useState(localStorage.getItem("auth_token") || "");
  const [user, setUser] = useState<{username: string; role: string} | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    if (token) {
      api.auth.me().then(setUser).catch(() => { localStorage.removeItem("auth_token"); setToken(""); }).finally(() => setAuthChecked(true));
    } else {
      setAuthChecked(true);
    }
  }, [token]);

  const fetchAll = useCallback(async () => {
    try {
      const [c, s, sub, t] = await Promise.all([
        api.courses.list(), api.students.list(), api.subjects.list(), api.teachers.list(),
      ]);
      setCourses(c); setStudents(s); setSubjects(sub); setTeachers(t);
    } catch (e: any) { setError(e.message); }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  if (!authChecked) return <div className="h-screen flex items-center justify-center bg-[#0b1120]"><div className="animate-shimmer text-cyan-300/80">加载中...</div></div>;
  if (!token) return <LoginPage onLogin={(t: string) => { localStorage.setItem("auth_token", t); setToken(t); }} />;

  return (
    <div className="app-shell">
      <aside className="side-rail">
        <div className="brand-block">
          <div className="brand-mark"><GraduationCap /></div>
          <div className="brand-copy">
            <strong>智慧教务</strong>
            <span>Tutoring OS</span>
          </div>
        </div>
        <nav className="side-nav">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`side-nav-item ${
                tab === t.id ? "active" : ""
              }`}
            >
              <t.icon /> {t.label}
            </button>
          ))}
        </nav>
        <div className="side-meta">
          <strong>实时教学中枢</strong>
          <p>课程、考勤、成绩与 AI 学情分析统一协同</p>
        </div>
      </aside>
      <section className="flex flex-col flex-1 min-w-0">
        <header className="top-bar">
          <div className="top-bar-title">{TABS.find((t) => t.id === tab)?.label || "仪表盘"}</div>
          {user && (
            <div className="top-user">
              <span className="user-pill"><span className="dot" />{user.username}</span>
              <button onClick={async () => { try { await api.auth.logout(); setToken(""); setUser(null); } catch(e: any) {} }} className="logout-btn">
                <LogOut /> 退出
              </button>
            </div>
          )}
        </header>
      {error && (
        <div className="error-banner">
          <AlertTriangle className="w-4 h-4" /> {error}
          <button onClick={() => setError("")} className="ml-auto hover:bg-white/10 rounded-full p-0.5 transition-colors"><X className="w-4 h-4" /></button>
        </div>
      )}
      <main className="main-canvas" key={tab}>
        <div className="view-enter">
        {tab === "dashboard" && <DashboardView setError={setError} />}
        {tab === "schedule" && <ScheduleView courses={courses} students={students} subjects={subjects} teachers={teachers} onRefresh={fetchAll} setError={setError} />}
        {tab === "students" && <StudentsView students={students} onRefresh={fetchAll} setError={setError} />}
        {tab === "teachers" && <TeachersView teachers={teachers} subjects={subjects} onRefresh={fetchAll} setError={setError} />}
        {tab === "courses" && <CoursesView courses={courses} students={students} subjects={subjects} teachers={teachers} onRefresh={fetchAll} setError={setError} />}
        {tab === "attendance" && <AttendanceView courses={courses} students={students} onRefresh={fetchAll} setError={setError} />}
        {tab === "adjustments" && <AdjustmentsView courses={courses} subjects={subjects} teachers={teachers} onRefresh={fetchAll} setError={setError} />}
        {tab === "scores" && <ScoresView students={students} subjects={subjects} courses={courses} setError={setError} />}
        {tab === "analysis" && <AnalysisView students={students} setError={setError} />}
        {tab === "ai-lab" && <AiLabView setError={setError} />}
        </div>
      </main>
      </section>
    </div>
  );
}

function ScheduleView({ courses, students, subjects, teachers, onRefresh, setError }: {
  courses: Course[]; students: Student[]; subjects: Subject[]; teachers: Teacher[];
  onRefresh: () => void; setError: (e: string) => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Course | null>(null);

  return (
    <div className="view-page p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-800">周排课表</h2>
        <button onClick={() => { setEditing(null); setShowForm(true); }} className="primary-btn">
          <Plus className="w-4 h-4" /> 添加课程
        </button>
      </div>
      <div className="table-panel">
        <div className="grid grid-cols-[80px_repeat(7,1fr)]">
          <div className="p-2 font-medium text-xs text-slate-400 table-head border-b border-r border-slate-100"></div>
          {DAY_NAMES.map((d) => (
            <div key={d} className="p-2 text-center font-medium text-xs text-slate-500 table-head border-b border-r border-slate-100">{d}</div>
          ))}
          {TIME_SLOTS.map((slot, si) => (
            <div key={si} className="contents">
              <div className="p-2 text-xs text-slate-400 table-head border-r border-b border-slate-100 flex items-center justify-center">{slot}</div>
              {[0,1,2,3,4,5,6].map((dow) => {
                const cellCourses = courses.filter((c) => c.day_of_week === dow && c.time_slot === si + 1);
                return (
                  <div key={`${dow}-${si}`} className="border-r border-b border-slate-100 p-1 min-h-[56px] hover:bg-white/8 transition-colors">
                    {cellCourses.map((c, ci) => (
                      <div key={c.id}
                        onClick={() => { setEditing(c); setShowForm(true); }}
                        className={`course-chip px-2 py-0.5 text-xs cursor-pointer ${getCourseColor(ci)}`}>
                        <div className="font-medium truncate">{c.subject?.name} {c.name}</div>
                        <div className="text-slate-500 truncate">{c.teacher?.name} · {c.student_count}人</div>
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
      {showForm && (
        <CourseFormModal
          course={editing} students={students} subjects={subjects} teachers={teachers}
          courses={courses}
          onClose={() => { setShowForm(false); setEditing(null); }}
          onSave={async () => { await onRefresh(); setShowForm(false); setEditing(null); }}
          setError={setError}
        />
      )}
    </div>
  );
}

function StudentsView({ students, onRefresh, setError }: {
  students: Student[]; onRefresh: () => void; setError: (e: string) => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Student | null>(null);
  const [filterGrade, setFilterGrade] = useState("");

  const filtered = filterGrade ? students.filter((s) => s.grade === filterGrade) : students;
  const allGrades = [...new Set(students.map((s) => s.grade))].sort();

  return (
    <div className="view-page p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-slate-800">学生管理</h2>
        <button onClick={() => { setEditing(null); setShowForm(true); }} className="primary-btn">
          <Plus className="w-4 h-4" /> 添加学生
        </button>
      </div>
      <div className="flex gap-2 mb-3 flex-wrap">
        <button onClick={() => setFilterGrade("")} className={`chip ${!filterGrade ? "active" : ""}`}>全部</button>
        {allGrades.map((g) => (
          <button key={g} onClick={() => setFilterGrade(g)} className={`chip ${filterGrade === g ? "active" : ""}`}>{g}</button>
        ))}
      </div>
      <div className="table-panel">
        <div className="grid grid-cols-[1fr_80px_120px_1fr_80px] gap-2 px-4 py-2 table-head border-b border-slate-100 text-xs font-medium text-slate-400">
          <div>姓名</div><div>学段</div><div>年级</div><div>电话</div><div></div>
        </div>
        {filtered.map((s) => (
          <div key={s.id} className="grid grid-cols-[1fr_80px_120px_1fr_80px] gap-2 px-4 py-2.5 border-b border-slate-100 text-sm items-center hover:bg-white/8 transition-colors">
            <div className="font-medium text-slate-800">{s.name}</div>
            <div className="text-xs text-slate-400">{s.grade_level}</div>
            <div className="text-xs text-slate-400">{s.grade}</div>
            <div className="text-xs text-slate-400">{s.phone || "—"}</div>
            <div className="flex gap-1 justify-end">
              <button onClick={() => { setEditing(s); setShowForm(true); }} className="icon-btn"><Edit3 className="w-3.5 h-3.5 text-slate-400" /></button>
              <button onClick={async () => { try { await api.students.delete(s.id); onRefresh(); } catch (e: any) { setError(e.message); } }} className="icon-btn"><Trash2 className="w-3.5 h-3.5 text-red-400" /></button>
            </div>
          </div>
        ))}
      </div>
      {showForm && (
        <StudentFormModal
          student={editing} onClose={() => { setShowForm(false); setEditing(null); }}
          onSave={async () => { await onRefresh(); setShowForm(false); setEditing(null); }}
          setError={setError}
        />
      )}
    </div>
  );
}

function CoursesView({ courses, students, subjects, teachers, onRefresh, setError }: {
  courses: Course[]; students: Student[]; subjects: Subject[]; teachers: Teacher[];
  onRefresh: () => void; setError: (e: string) => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Course | null>(null);

  return (
    <div className="view-page p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-800">课程管理</h2>
        <button onClick={() => { setEditing(null); setShowForm(true); }} className="primary-btn">
          <Plus className="w-4 h-4" /> 添加课程
        </button>
      </div>
      <div className="table-panel">
        <div className="grid grid-cols-[1fr_80px_80px_80px_100px_80px_100px_80px] gap-2 px-4 py-2 table-head border-b border-slate-100 text-xs font-medium text-slate-400">
          <div>课程名</div><div>科目</div><div>教师</div><div>教室</div><div>时间</div><div>类型</div><div>学生</div><div></div>
        </div>
        {courses.map((c) => (
          <div key={c.id} className="grid grid-cols-[1fr_80px_80px_80px_100px_80px_100px_80px] gap-2 px-4 py-2.5 border-b border-slate-100 text-sm items-center hover:bg-white/8 transition-colors">
            <div className="font-medium text-gray-800 truncate">{c.name}</div>
            <div className="text-xs text-slate-400">{c.subject?.name || "—"}</div>
            <div className="text-xs text-gray-500 truncate">{c.teacher?.name || "—"}</div>
            <div className="text-xs text-slate-400">{c.room?.name || "—"}</div>
            <div className="text-xs text-slate-400">{DAY_NAMES[c.day_of_week]} {TIME_SLOTS[c.time_slot - 1]}</div>
            <div className={`status-chip text-xs px-1.5 py-0.5 ${c.course_type === "class" ? "status-class" : "status-study"}`}>
              {COURSE_TYPES[c.course_type] || c.course_type}
            </div>
            <div className="text-xs text-slate-400">{c.student_count}/{c.max_students}</div>
            <div className="flex gap-1 justify-end">
              <button onClick={() => { setEditing(c); setShowForm(true); }} className="icon-btn"><Edit3 className="w-3.5 h-3.5 text-slate-400" /></button>
              <button onClick={async () => { try { await api.courses.delete(c.id); onRefresh(); } catch (e: any) { setError(e.message); } }} className="icon-btn"><Trash2 className="w-3.5 h-3.5 text-red-400" /></button>
            </div>
          </div>
        ))}
      </div>
      {showForm && (
        <CourseFormModal
          course={editing} students={students} subjects={subjects} teachers={teachers}
          courses={courses}
          onClose={() => { setShowForm(false); setEditing(null); }}
          onSave={async () => { await onRefresh(); setShowForm(false); setEditing(null); }}
          setError={setError}
        />
      )}
    </div>
  );
}

function StudentFormModal({ student, onClose, onSave, setError }: {
  student: Student | null; onClose: () => void; onSave: () => void; setError: (e: string) => void;
}) {
  const [name, setName] = useState(student?.name || "");
  const [gradeLevel, setGradeLevel] = useState(student?.grade_level || "初中");
  const [grade, setGrade] = useState(student?.grade || "初一");
  const [phone, setPhone] = useState(student?.phone || "");
  const [notes, setNotes] = useState(student?.notes || "");
  const [saving, setSaving] = useState(false);

  const grades = gradeLevel === "初中" ? JUNIOR_GRADES : SENIOR_GRADES;

  useEffect(() => { if (!JUNIOR_GRADES.includes(grade) && gradeLevel === "初中") setGrade("初一"); if (!SENIOR_GRADES.includes(grade) && gradeLevel === "高中") setGrade("高一"); }, [gradeLevel, grade]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault(); setSaving(true);
    try {
      const data = { name, grade_level: gradeLevel, grade, phone, notes };
      if (student) await api.students.update(student.id, data);
      else await api.students.create(data);
      onSave();
    } catch (e: any) { setError(e.message); }
    finally { setSaving(false); }
  };

  return (
    <Modal onClose={onClose}>
      <div className="modal-card w-[420px] max-h-[80vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h3 className="font-semibold text-slate-800">{student ? "编辑学生" : "添加学生"}</h3>
          <button onClick={onClose} className="hover:rotate-90 transition-transform duration-200"><X className="w-5 h-5 text-slate-400 hover:text-slate-600" /></button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">姓名</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required className="field" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">学段</label>
            <div className="flex gap-2">
              {GRADE_LEVELS.map((gl) => (
                <button key={gl} type="button" onClick={() => setGradeLevel(gl)} className={`chip ${gradeLevel === gl ? "active" : ""}`}>{gl}</button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">年级</label>
            <div className="flex gap-2 flex-wrap">
              {grades.map((g) => (
                <button key={g} type="button" onClick={() => setGrade(g)} className={`chip ${grade === g ? "active" : ""}`}>{g}</button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">电话</label>
            <input value={phone} onChange={(e) => setPhone(e.target.value)} className="field" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">备注</label>
            <input value={notes} onChange={(e) => setNotes(e.target.value)} className="field" />
          </div>
          <button type="submit" disabled={saving} className="primary-btn w-full">
            <Save className="w-4 h-4" /> {saving ? "保存中..." : "保存"}
          </button>
        </form>
      </div>
    </Modal>
  );
}

function CourseFormModal({ course, students, subjects, teachers, courses: _courses, onClose, onSave, setError }: {
  course: Course | null; students: Student[]; subjects: Subject[]; teachers: Teacher[];
  courses: Course[]; onClose: () => void; onSave: () => void; setError: (e: string) => void;
}) {
  const [name, setName] = useState(course?.name || "");
  const [subjectId, setSubjectId] = useState(course?.subject_id || subjects[0]?.id || 0);
  const [teacherId, setTeacherId] = useState(course?.teacher_id || teachers[0]?.id || 0);
  const [roomId, setRoomId] = useState(course?.room_id || 1);
  const [dayOfWeek, setDayOfWeek] = useState(course?.day_of_week ?? 0);
  const [timeSlot, setTimeSlot] = useState(course?.time_slot ?? 1);
  const [courseType, setCourseType] = useState(course?.course_type || "class");
  const [maxStudents, setMaxStudents] = useState(course?.max_students ?? 8);
  const [notes, setNotes] = useState(course?.notes || "");
  const [selectedStudents, setSelectedStudents] = useState<number[]>(course?.students?.map((s) => s.id) || []);
  const [saving, setSaving] = useState(false);

  const roomNames = ["1号教室", "2号教室", "3号教室", "4号教室", "5号教室"];

  const toggleStudent = (sid: number) => {
    setSelectedStudents((prev) => prev.includes(sid) ? prev.filter((id) => id !== sid) : [...prev, sid]);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault(); setSaving(true);
    try {
      const data = { name, subject_id: subjectId, teacher_id: teacherId, room_id: roomId, day_of_week: dayOfWeek, time_slot: timeSlot, course_type: courseType, max_students: maxStudents, notes, student_ids: selectedStudents };
      if (course) await api.courses.update(course.id, data);
      else await api.courses.create(data);
      onSave();
    } catch (e: any) { setError(e.message); }
    finally { setSaving(false); }
  };

  return (
    <Modal onClose={onClose}>
      <div className="modal-card w-[520px] max-h-[85vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h3 className="font-semibold text-slate-800">{course ? "编辑课程" : "添加课程"}</h3>
          <button onClick={onClose} className="hover:rotate-90 transition-transform duration-200"><X className="w-5 h-5 text-slate-400 hover:text-slate-600" /></button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">课程名称</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required className="field" placeholder="如：高一数学冲刺班" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">科目</label>
              <select value={subjectId} onChange={(e) => setSubjectId(Number(e.target.value))} className="field">
                {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">教师</label>
              <select value={teacherId} onChange={(e) => setTeacherId(Number(e.target.value))} className="field">
                <option value={0}>请选择</option>
                {teachers.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">教室</label>
              <select value={roomId} onChange={(e) => setRoomId(Number(e.target.value))} className="field">
                {[1,2,3,4,5].map((r) => <option key={r} value={r}>{roomNames[r-1]}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">星期</label>
              <select value={dayOfWeek} onChange={(e) => setDayOfWeek(Number(e.target.value))} className="field">
                {DAY_NAMES.map((d, i) => <option key={i} value={i}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">时段</label>
              <select value={timeSlot} onChange={(e) => setTimeSlot(Number(e.target.value))} className="field">
                {TIME_SLOTS.map((t, i) => <option key={i} value={i + 1}>{t}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">类型</label>
              <div className="flex gap-2">
                <button type="button" onClick={() => { setCourseType("class"); if (roomId === 5) setRoomId(1); setMaxStudents(8); }} className={`chip ${courseType === "class" ? "active" : ""}`}>课程</button>
                <button type="button" onClick={() => { setCourseType("self_study"); setRoomId(5); setMaxStudents(15); }} className={`chip ${courseType === "self_study" ? "active" : ""}`}>自习</button>
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">人数上限</label>
              <input type="number" value={maxStudents} onChange={(e) => setMaxStudents(Number(e.target.value))} min={1} max={15} className="field" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">备注</label>
            <input value={notes} onChange={(e) => setNotes(e.target.value)} className="field" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">学生</label>
            <div className="panel max-h-32 overflow-auto p-2 space-y-1">
              {students.length === 0 && <div className="text-xs text-gray-400 py-2 text-center">暂无学生，请先添加</div>}
              {students.map((s) => (
                <label key={s.id} className="flex items-center gap-2 text-sm cursor-pointer hover:bg-white/8 px-1 py-0.5 rounded-2xl transition-colors">
                  <input type="checkbox" checked={selectedStudents.includes(s.id)} onChange={() => toggleStudent(s.id)} className="rounded-2xl" />
                  <span className="text-gray-700">{s.name}</span>
                  <span className="text-xs text-gray-400">{s.grade}</span>
                </label>
              ))}
            </div>
          </div>
          <button type="submit" disabled={saving} className="primary-btn w-full">
            <Save className="w-4 h-4" /> {saving ? "保存中..." : "保存"}
          </button>
        </form>
      </div>
    </Modal>
  );
}

function TeachersView({ teachers, subjects, onRefresh, setError }: {
  teachers: Teacher[]; subjects: Subject[]; onRefresh: () => void; setError: (e: string) => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Teacher | null>(null);

  return (
    <div className="view-page p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-800">教师管理</h2>
        <button onClick={() => { setEditing(null); setShowForm(true); }} className="primary-btn">
          <Plus className="w-4 h-4" /> 添加教师
        </button>
      </div>
      <div className="table-panel">
        <div className="grid grid-cols-[1fr_120px_1fr_80px] gap-2 px-4 py-2 table-head border-b border-slate-100 text-xs font-medium text-slate-400">
          <div>姓名</div><div>电话</div><div>教授科目</div><div></div>
        </div>
        {teachers.map((t) => (
          <div key={t.id} className="grid grid-cols-[1fr_120px_1fr_80px] gap-2 px-4 py-2.5 border-b border-slate-100 text-sm items-center hover:bg-white/8 transition-colors">
            <div className="font-medium text-slate-800">{t.name}</div>
            <div className="text-xs text-slate-400">{t.phone || "—"}</div>
            <div className="text-xs text-slate-400">{t.subjects?.map((s) => s.name).join("、") || "—"}</div>
            <div className="flex gap-1 justify-end">
              <button onClick={() => { setEditing(t); setShowForm(true); }} className="icon-btn"><Edit3 className="w-3.5 h-3.5 text-slate-400" /></button>
              <button onClick={async () => { try { await api.teachers.delete(t.id); onRefresh(); } catch (e: any) { setError(e.message); } }} className="icon-btn"><Trash2 className="w-3.5 h-3.5 text-red-400" /></button>
            </div>
          </div>
        ))}
        {teachers.length === 0 && <div className="text-sm text-gray-400 text-center py-8 col-span-4">暂无教师，请添加</div>}
      </div>
      {showForm && (
        <TeacherFormModal
          teacher={editing} subjects={subjects}
          onClose={() => { setShowForm(false); setEditing(null); }}
          onSave={async () => { await onRefresh(); setShowForm(false); setEditing(null); }}
          setError={setError}
        />
      )}
    </div>
  );
}

function TeacherFormModal({ teacher, subjects, onClose, onSave, setError }: {
  teacher: Teacher | null; subjects: Subject[]; onClose: () => void; onSave: () => void; setError: (e: string) => void;
}) {
  const [name, setName] = useState(teacher?.name || "");
  const [phone, setPhone] = useState(teacher?.phone || "");
  const [notes, setNotes] = useState(teacher?.notes || "");
  const [selectedSubjects, setSelectedSubjects] = useState<number[]>(teacher?.subjects?.map((s) => s.id) || []);
  const [saving, setSaving] = useState(false);

  const toggleSubject = (sid: number) => {
    setSelectedSubjects((prev) => prev.includes(sid) ? prev.filter((id) => id !== sid) : [...prev, sid]);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault(); setSaving(true);
    try {
      const data = { name, phone, notes, subject_ids: selectedSubjects };
      if (teacher) await api.teachers.update(teacher.id, data);
      else await api.teachers.create(data);
      onSave();
    } catch (e: any) { setError(e.message); }
    finally { setSaving(false); }
  };

  return (
    <Modal onClose={onClose}>
      <div className="modal-card w-[420px] max-h-[80vh]" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h3 className="font-semibold text-slate-800">{teacher ? "编辑教师" : "添加教师"}</h3>
          <button onClick={onClose} className="hover:rotate-90 transition-transform duration-200"><X className="w-5 h-5 text-slate-400 hover:text-slate-600" /></button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">姓名</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required className="field" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">电话</label>
            <input value={phone} onChange={(e) => setPhone(e.target.value)} className="field" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">备注</label>
            <input value={notes} onChange={(e) => setNotes(e.target.value)} className="field" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">教授科目</label>
            <div className="panel max-h-40 overflow-auto p-2 space-y-1">
              {subjects.map((s) => (
                <label key={s.id} className="flex items-center gap-2 text-sm cursor-pointer hover:bg-white/8 px-1 py-0.5 rounded-2xl transition-colors">
                  <input type="checkbox" checked={selectedSubjects.includes(s.id)} onChange={() => toggleSubject(s.id)} className="rounded-2xl" />
                  <span className="text-gray-700">{s.name}</span>
                </label>
              ))}
            </div>
          </div>
          <button type="submit" disabled={saving} className="primary-btn w-full">
            <Save className="w-4 h-4" /> {saving ? "保存中..." : "保存"}
          </button>
        </form>
      </div>
    </Modal>
  );
}



function LoginPage({ onLogin }: { onLogin: (token: string) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMsg("");
    try {
      if (mode === "login") {
        const res = await api.auth.login(username, password);
        localStorage.setItem("auth_token", res.token);
        onLogin(res.token);
      } else {
        await api.auth.register(username, password);
        setMsg("注册成功，请登录");
        setMode("login");
      }
    } catch (e: any) {
      setMsg(e.message || "操作失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-stage">
      <div className="login-visual">
        <div className="login-radar">
          <div className="login-radar-core"><GraduationCap /></div>
        </div>
      </div>
      <div className="login-card">
        <h1>
          <GraduationCap className="w-6 h-6 text-cyan-300" />
          补习班教务管理系统
        </h1>
        <h2>{mode === "login" ? "欢迎回来，继续你的教学管理" : "创建你的教务工作台"}</h2>
        <form onSubmit={handleSubmit}>
          <label htmlFor="login-username">用户名</label>
          <input id="login-username" value={username} onChange={(e) => setUsername(e.target.value)} required autoComplete="username" />
          <label htmlFor="login-password">密码</label>
          <input id="login-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete={mode === "login" ? "current-password" : "new-password"} />
          {msg && <div className="login-message">{msg}</div>}
          <button type="submit" disabled={loading} className="primary-btn w-full !py-3">
            {loading ? "处理中..." : mode === "login" ? "登录" : "注册"}
          </button>
        </form>
        <button onClick={() => { setMode(mode === "login" ? "register" : "login"); setMsg(""); }} className="login-switch">
          {mode === "login" ? "没有账号？注册" : "已有账号？登录"}
        </button>
      </div>
    </div>
  );
}

function AttendanceView({ courses, students: _students, onRefresh: _onRefresh, setError }: {
  courses: Course[]; students: Student[]; onRefresh: () => void; setError: (e: string) => void;
}) {
  const [courseId, setCourseId] = useState<number>(0);
  const [dateVal, setDateVal] = useState(new Date().toISOString().split("T")[0]);
  const [records, setRecords] = useState<Record<number, { status: string; notes: string }>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [activeView, setActiveView] = useState<"checkin" | "analysis">("checkin");
  const [attData, setAttData] = useState<AttendanceAnalysis | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [filterGradeLevel, setFilterGradeLevel] = useState("");
  const [filterGrade, setFilterGrade] = useState("");

  const selectedCourse = courses.find((c) => c.id === courseId);
  const enrolledStudents = selectedCourse?.students || [];

  useEffect(() => {
    if (!courseId || !dateVal) return;
    setSaved(false);
    api.attendance.list(courseId, dateVal).then((att) => {
      const m: Record<number, { status: string; notes: string }> = {};
      att.forEach((a) => { m[a.student_id] = { status: a.status, notes: a.notes }; });
      setRecords(m);
    }).catch(() => {});
  }, [courseId, dateVal]);

  useEffect(() => {
    if (activeView === "analysis") {
      setReportLoading(true);
        api.analysis.attendance().then(setAttData).catch((e: any) => { setError(e.message || "加载失败"); }).finally(() => setReportLoading(false));
    }
  }, [activeView]);

  const updateRecord = (sid: number, field: "status" | "notes", value: string) => {
    setRecords((prev) => ({ ...prev, [sid]: { ...prev[sid], status: prev[sid]?.status || "present", [field]: value } }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const recs = enrolledStudents.map((s) => ({
        student_id: s.id,
        status: records[s.id]?.status || "present",
        notes: records[s.id]?.notes || "",
      }));
      await api.attendance.batch({ course_id: courseId, date_val: dateVal, records: recs });
      setSaved(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="view-page p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-800">考勤管理</h2>
        <div className="flex gap-1">
          {[ ["checkin","打卡"], ["analysis","考勤分析"] ].map(([id,label]) => (
            <button key={id} onClick={() => setActiveView(id as any)} className={`chip ${activeView===id ? "active" : ""}`}>{label}</button>
          ))}
        </div>
      </div>
      {activeView === "checkin" ? (
        <>
          <div className="flex gap-4 mb-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">课程</label>
              <select value={courseId} onChange={(e) => setCourseId(Number(e.target.value))} className="field min-w-[200px]">
                <option value={0}>请选择课程</option>
                {courses.map((c) => (
                  <option key={c.id} value={c.id}>{c.name} ({c.subject?.name} · {c.teacher?.name})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">日期</label>
              <input type="date" value={dateVal} onChange={(e) => setDateVal(e.target.value)} className="field" />
            </div>
          </div>
          {courseId > 0 && enrolledStudents.length > 0 && (
            <>
              <div className="table-panel">
                <div className="grid grid-cols-[1fr_100px_1fr] gap-2 px-4 py-2 table-head border-b text-xs font-medium text-gray-500">
                  <div>学生</div><div>状态</div><div>备注</div>
                </div>
                {enrolledStudents.map((s) => (
                  <div key={s.id} className="grid grid-cols-[1fr_100px_1fr] gap-2 px-4 py-2.5 border-b text-sm items-center hover:bg-white/8">
                    <div className="font-medium text-slate-800">{s.name} <span className="text-xs text-gray-400">{s.grade}</span></div>
                    <div>
                      <select value={records[s.id]?.status || "present"} onChange={(e) => updateRecord(s.id, "status", e.target.value)} className="field !px-2 !py-1 text-xs">
                        <option value="present">出勤</option>
                        <option value="absent">缺勤</option>
                        <option value="late">迟到</option>
                        <option value="leave">请假</option>
                      </select>
                    </div>
                    <div>
                      <input value={records[s.id]?.notes || ""} onChange={(e) => updateRecord(s.id, "notes", e.target.value)} className="field !px-2 !py-1 text-xs" placeholder="备注" />
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-4 flex items-center gap-3">
                <button onClick={handleSave} disabled={saving} className="primary-btn">
                  <Save className="w-4 h-4" /> {saving ? "保存中..." : "保存考勤"}
                </button>
                {saved && <span className="text-xs text-green-600">已保存</span>}
              </div>
            </>
          )}
          {courseId > 0 && enrolledStudents.length === 0 && (
            <div className="text-sm text-gray-400 py-8 text-center panel">该课程暂无学生，请先在课程管理中添加学生</div>
          )}
        </>
      ) : (
        <div className="space-y-4">
            <div className="flex gap-2 flex-wrap items-center">
              <input value={searchText} onChange={e=>setSearchText(e.target.value)} placeholder="搜索学生姓名..." className="field field-auto min-w-[180px]" />
              <select value={filterGradeLevel} onChange={e=>{setFilterGradeLevel(e.target.value);setFilterGrade("")}} className="field field-auto"><option value="">全部学段</option><option value="初中">初中</option><option value="高中">高中</option></select>
              {filterGradeLevel && <select value={filterGrade} onChange={e=>setFilterGrade(e.target.value)} className="field field-auto"><option value="">全部年级</option>{(filterGradeLevel==="初中"?["初一","初二","初三"]:["高一","高二","高三"]).map(g=><option key={g} value={g}>{g}</option>)}</select>}
            </div>
            {reportLoading && <div className="text-sm text-slate-400 py-8 text-center">加载中...</div>}
            {!reportLoading && attData && (()=>{
              const d=attData as any;
              let students = d.by_student.filter((s:any)=>s.student);
              if(searchText) students=students.filter((s:any)=>s.student.name.includes(searchText));
              if(filterGradeLevel) students=students.filter((s:any)=>s.student.grade_level===filterGradeLevel);
              if(filterGrade) students=students.filter((s:any)=>s.student.grade===filterGrade);
              return <>
                <div className="grid grid-cols-5 gap-3">
                  {[{l:"总记录",v:d.summary.total,c:"text-slate-700"},{l:"出勤率",v:d.summary.rate+"%",c:"text-green-600"},{l:"出勤",v:d.summary.present,c:"text-green-600"},{l:"迟到",v:d.summary.late,c:"text-amber-600"},{l:"缺勤+请假",v:d.summary.absent+d.summary.leave,c:"text-red-500"}].map((x:any)=><div key={x.l} className="stat-tile p-3 text-center"><div className="text-xs text-slate-400">{x.l}</div><div className={`text-lg font-bold ${x.c}`}>{x.v}</div></div>)}
                </div>
                <div className="table-panel">
                  <div className="grid grid-cols-[1fr_80px_120px_80px_80px] gap-2 px-4 py-2 table-head border-b text-xs font-medium text-slate-400"><div>学生</div><div>年级</div><div className="text-center">出勤率</div><div>出勤</div><div>缺+请</div></div>
                  {students.map((s:any)=><div key={s.student.id} className="grid grid-cols-[1fr_80px_120px_80px_80px] gap-2 px-4 py-2 border-b last:border-0 text-sm items-center hover:bg-white/8"><div className="font-medium text-slate-800">{s.student.name}</div><div className="text-xs text-slate-400">{s.student.grade}</div><div className="flex items-center gap-2"><div className="flex-1 h-2 progress-track"><div className={`h-full rounded-full ${s.rate>=90?"fill-good":s.rate>=75?"fill-mid":"fill-low"}`} style={{width:`${s.rate}%`}}/></div><span className="text-xs font-medium w-12 text-right">{s.rate}%</span></div><div className="text-xs text-green-600">{s.present}</div><div className="text-xs text-red-500">{s.absent+s.leave}</div></div>)}
                  {students.length===0 && <div className="text-xs text-slate-400 py-6 text-center">无匹配结果</div>}
                </div>
              </>})()}
          </div>
      ) }
    </div>
  );
}

function AdjustmentsView({ courses, subjects: _subjects, teachers: _teachers, onRefresh: _onRefresh, setError }: {
  courses: Course[]; subjects: Subject[]; teachers: Teacher[];
  onRefresh: () => void; setError: (e: string) => void;
}) {
  const [adjustments, setAdjustments] = useState<ScheduleAdjustment[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<ScheduleAdjustment | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    setLoading(true);
    try { setAdjustments(await api.adjustments.list()); } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="view-page p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-800">课程调整记录</h2>
        <button onClick={() => { setEditing(null); setShowForm(true); }} className="primary-btn">
          <Plus className="w-4 h-4" /> 添加调整
        </button>
      </div>
      {loading ? (
        <div className="text-sm text-gray-400 py-8 text-center panel">加载中...</div>
      ) : adjustments.length === 0 ? (
        <div className="text-sm text-gray-400 py-8 text-center panel">暂无调课记录</div>
      ) : (
        <div className="table-panel">
          <div className="grid grid-cols-[1fr_100px_100px_100px_100px_80px_80px] gap-2 px-4 py-2 table-head border-b text-xs font-medium text-gray-500">
            <div>课程</div><div>调整日期</div><div>原时间</div><div>新时间</div><div>类型</div><div>原因</div><div></div>
          </div>
          {adjustments.map((adj) => (
            <div key={adj.id} className="grid grid-cols-[1fr_100px_100px_100px_100px_80px_80px] gap-2 px-4 py-2.5 border-b text-sm items-center hover:bg-white/8">
              <div className="font-medium text-gray-800 truncate">{adj.course?.name || "—"}</div>
              <div className="text-xs text-slate-400">{adj.adjustment_date}</div>
              <div className="text-xs text-slate-400">{DAY_NAMES[adj.original_day]} {TIME_SLOTS[adj.original_slot - 1]}</div>
              <div className="text-xs text-slate-400">
                {adj.new_day !== null && adj.new_slot !== null ? `${DAY_NAMES[adj.new_day]} ${TIME_SLOTS[adj.new_slot - 1]}` : "取消"}
              </div>
              <div className={`status-chip text-xs px-1.5 py-0.5 ${adj.adjustment_type === "rescheduled" ? "status-reschedule" : "status-cancel"}`}>
                {adj.adjustment_type === "rescheduled" ? "调课" : adj.adjustment_type === "cancelled" ? "停课" : adj.adjustment_type}
              </div>
              <div className="text-xs text-gray-500 truncate">{adj.reason || "—"}</div>
              <div className="flex gap-1 justify-end">
                <button onClick={async () => { try { await api.adjustments.delete(adj.id); load(); } catch(e: any) { setError(e.message); } }} className="icon-btn"><Trash2 className="w-3.5 h-3.5 text-red-400" /></button>
              </div>
            </div>
          ))}
        </div>
      )}
      {showForm && (
        <AdjustmentFormModal
          adjustment={editing} courses={courses}
          onClose={() => { setShowForm(false); setEditing(null); }}
          onSave={async () => { await load(); setShowForm(false); setEditing(null); }}
          setError={setError}
        />
      )}
    </div>
  );
}

function AdjustmentFormModal({ adjustment, courses, onClose, onSave, setError }: {
  adjustment: ScheduleAdjustment | null; courses: Course[];
  onClose: () => void; onSave: () => void; setError: (e: string) => void;
}) {
  const [courseId, setCourseId] = useState(adjustment?.course_id || 0);
  const [adjustmentDate, setAdjustmentDate] = useState(adjustment?.adjustment_date || new Date().toISOString().split("T")[0]);
  const [adjustmentType, setAdjustmentType] = useState(adjustment?.adjustment_type || "rescheduled");
  const [newDay, setNewDay] = useState(adjustment?.new_day ?? 0);
  const [newSlot, setNewSlot] = useState(adjustment?.new_slot ?? 1);
  const [newRoomId, setNewRoomId] = useState(adjustment?.new_room_id ?? 1);
  const [reason, setReason] = useState(adjustment?.reason || "");
  const [saving, setSaving] = useState(false);

  const selectedCourse = courses.find((c) => c.id === courseId);
  const roomNames = ["1号教室", "2号教室", "3号教室", "4号教室", "5号教室"];

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const data = {
        course_id: courseId,
        adjustment_date: adjustmentDate,
        original_day: selectedCourse?.day_of_week ?? 0,
        original_slot: selectedCourse?.time_slot ?? 1,
        original_room_id: selectedCourse?.room_id ?? 1,
        new_day: adjustmentType === "cancelled" ? undefined : newDay,
        new_slot: adjustmentType === "cancelled" ? undefined : newSlot,
        new_room_id: adjustmentType === "cancelled" ? undefined : newRoomId,
        adjustment_type: adjustmentType,
        reason,
      };
      await api.adjustments.create(data);
      onSave();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal onClose={onClose}>
      <div className="modal-card w-[480px] max-h-[85vh]" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h3 className="font-semibold text-slate-800">添加课程调整</h3>
          <button onClick={onClose} className="hover:rotate-90 transition-transform duration-200"><X className="w-5 h-5 text-slate-400 hover:text-slate-600" /></button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">课程</label>
            <select value={courseId} onChange={(e) => setCourseId(Number(e.target.value))} className="field">
              <option value={0}>请选择课程</option>
              {courses.map((c) => (
                <option key={c.id} value={c.id}>{c.name} ({c.subject?.name} · {DAY_NAMES[c.day_of_week]} {TIME_SLOTS[c.time_slot - 1]})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">调整日期</label>
            <input type="date" value={adjustmentDate} onChange={(e) => setAdjustmentDate(e.target.value)} className="field" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">调整类型</label>
            <div className="flex gap-2">
              <button type="button" onClick={() => setAdjustmentType("rescheduled")} className={`chip ${adjustmentType === "rescheduled" ? "active" : ""}`}>调课</button>
              <button type="button" onClick={() => setAdjustmentType("cancelled")} className={`chip ${adjustmentType === "cancelled" ? "active" : ""}`}>停课</button>
            </div>
          </div>
          {adjustmentType === "rescheduled" && (
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">新星期</label>
                <select value={newDay} onChange={(e) => setNewDay(Number(e.target.value))} className="field">
                  {DAY_NAMES.map((d, i) => <option key={i} value={i}>{d}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">新时段</label>
                <select value={newSlot} onChange={(e) => setNewSlot(Number(e.target.value))} className="field">
                  {TIME_SLOTS.map((t, i) => <option key={i} value={i + 1}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">新教室</label>
                <select value={newRoomId} onChange={(e) => setNewRoomId(Number(e.target.value))} className="field">
                  {[1, 2, 3, 4, 5].map((r) => <option key={r} value={r}>{roomNames[r - 1]}</option>)}
                </select>
              </div>
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">原因</label>
            <input value={reason} onChange={(e) => setReason(e.target.value)} className="field" placeholder="如：老师请假、教室维修等" />
          </div>
          <button type="submit" disabled={saving || courseId === 0} className="primary-btn w-full">
            <Save className="w-4 h-4" /> {saving ? "保存中..." : "保存调整"}
          </button>
        </form>
      </div>
    </Modal>
  );
}
