import { useEffect, useState, type CSSProperties } from "react";
import {
  Activity, AlertTriangle, BookOpen, CalendarDays, DoorOpen,
  GraduationCap, Presentation, RefreshCw, Sparkles, TrendingDown, TrendingUp, Users,
} from "lucide-react";
import { api } from "./api";
import { ReportContent } from "./Analytics";
import type { AiInsightResult, CourseHealthItem, DashboardData, RiskStudentItem } from "./types";
import { DAY_NAMES, TIME_SLOTS, ROOM_TYPES } from "./types";

function CountUp({ value, decimals = 0 }: { value: number; decimals?: number }) {
  const [display, setDisplay] = useState("0");
  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const duration = 850;
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(decimals ? (value * eased).toFixed(decimals) : String(Math.round(value * eased)));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, decimals]);
  return <>{display}</>;
}

function KpiGrid({ data }: { data: DashboardData }) {
  const items = [
    { label: "在籍学生", value: data.counts.students, decimals: 0, icon: Users, tone: "blue" },
    { label: "教师", value: data.counts.teachers, decimals: 0, icon: Presentation, tone: "green" },
    { label: "课程", value: data.counts.courses, decimals: 0, icon: BookOpen, tone: "gold" },
    { label: "科目", value: data.counts.subjects, decimals: 0, icon: GraduationCap, tone: "violet" },
    { label: "整体出勤率", value: data.attendance.rate, decimals: 1, icon: Activity, tone: "green" },
    { label: "成绩得分率", value: data.scores.avg_rate, decimals: 1, icon: TrendingUp, tone: "gold" },
  ];
  return (
    <div className="dash-kpi-grid">
      {items.map((it) => (
        <div key={it.label} className={`stat-tile dash-kpi tone-${it.tone}`}>
          <it.icon className="dash-kpi-icon" />
          <div className="dash-kpi-value">
            <CountUp value={it.value} decimals={it.decimals} />
            {it.decimals ? "%" : ""}
          </div>
          <div className="dash-kpi-label">{it.label}</div>
        </div>
      ))}
    </div>
  );
}

function TodayModule({ data }: { data: DashboardData }) {
  const today = data.today_courses;
  return (
    <section className="dash-module dash-module-today">
      <div className="dash-module-head">
        <div>
          <h3>今日课程</h3>
          <p>{data.today_date} · {DAY_NAMES[data.today_dow]} · {today.length} 节课 · {data.today_student_seats} 人次</p>
        </div>
        <span className="status-chip status-ok">今日考勤 {data.today_attendance.present}/{data.today_attendance.total}</span>
      </div>
      <div className="dash-today-grid">
        <div className="today-timeline">
          {TIME_SLOTS.map((slot, si) => {
            const slotCourses = today.filter((c) => c.time_slot === si + 1);
            return (
              <div key={slot} className="timeline-row">
                <div className="timeline-time">{slot}</div>
                <div className="timeline-courses">
                  {slotCourses.length === 0 && <span className="timeline-empty">空闲</span>}
                  {slotCourses.map((c) => (
                    <div key={c.id} className="timeline-course">
                      <div className="timeline-course-title">{c.name}</div>
                      <div className="timeline-course-meta">
                        <span>{c.subject?.name}</span>
                        <span>{c.teacher?.name}</span>
                        <span>{c.room?.name}</span>
                        <span>{c.student_count}/{c.max_students}人</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
        <div className="room-occupancy">
          <h4>教室占用</h4>
          {data.room_occupancy.map((r) => {
            const pct = Math.min(100, (r.today_courses / Math.max(1, data.today_courses.length)) * 100);
            return (
              <div key={r.room_id} className="room-occ-row">
                <div className="room-occ-head">
                  <span><DoorOpen /> {r.room_name}</span>
                  <span>{ROOM_TYPES[r.room_type] || r.room_type} · {r.today_courses}节</span>
                </div>
                <div className="progress-track"><div className="fill-mid" style={{ width: `${pct}%` }} /></div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function WeeklyModule({ data }: { data: DashboardData }) {
  const max = Math.max(1, ...data.weekly_load);
  return (
    <section className="dash-module">
      <div className="dash-module-head">
        <div>
          <h3>周负载</h3>
          <p>各星期课程量与时段分布</p>
        </div>
        <CalendarDays className="dash-module-icon" />
      </div>
      <div className="week-bars">
        {DAY_NAMES.map((d, i) => (
          <div key={d} className="week-bar-col">
            <div className="week-bar-track">
              <div className="week-bar-fill" style={{ height: `${(data.weekly_load[i] / max) * 100}%` }}>
                <span>{data.weekly_load[i]}</span>
              </div>
            </div>
            <div className="week-bar-label">{d.replace("周", "")}</div>
          </div>
        ))}
      </div>
      <div className="slot-load">
        {data.slot_load.map((count, i) => (
          <div key={i} className="slot-load-item">
            <span>{i + 1}</span>
            <div className="progress-track"><div className="fill-good" style={{ width: `${(count / Math.max(1, ...data.slot_load)) * 100}%` }} /></div>
            <b>{count}</b>
          </div>
        ))}
      </div>
    </section>
  );
}

function SubjectModule({ data }: { data: DashboardData }) {
  return (
    <section className="dash-module">
      <div className="dash-module-head">
        <div>
          <h3>科目表现</h3>
          <p>出勤率与得分率对比</p>
        </div>
        <BookOpen className="dash-module-icon" />
      </div>
      <div className="subject-bars">
        {data.subject_metrics.map((m) => (
          <div key={m.subject_id} className="subject-bar-col">
            <div className="subject-bar-track">
              <div className="subject-bar att" style={{ height: `${m.attendance_rate}%` }} />
              <div className="subject-bar score" style={{ height: `${m.score_rate}%` }} />
            </div>
            <div className="subject-bar-label" title={`${m.subject} · 出勤${m.attendance_rate}% · 成绩${m.score_rate}%`}>
              {m.subject}
            </div>
          </div>
        ))}
      </div>
      <div className="subject-legend">
        <span><i className="legend-dot dot-green" />出勤率</span>
        <span><i className="legend-dot dot-orange" />得分率</span>
      </div>
    </section>
  );
}

function LineChart({ points, color }: { points: { label: string; value: number }[]; color: string }) {
  if (points.length < 2) return <div className="chart-empty">数据不足，暂无趋势</div>;
  const W = 340, H = 130, P = 12;
  const max = Math.max(100, ...points.map((p) => p.value));
  const stepX = (W - P * 2) / Math.max(1, points.length - 1);
  const coords = points.map((p, i) => ({
    x: P + i * stepX,
    y: H - P - (p.value / max) * (H - P * 2),
  }));
  const line = coords.map((c) => `${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
  const area = `${P},${H - P} ${line} ${coords[coords.length - 1].x.toFixed(1)},${H - P}`;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="line-chart-svg">
      {[0.25, 0.5, 0.75, 1].map((f) => (
        <line key={f} x1={P} x2={W - P} y1={H - P - f * (H - P * 2)} y2={H - P - f * (H - P * 2)} className="chart-grid-line" />
      ))}
      <polygon points={area} fill={color} opacity="0.12" />
      <polyline points={line} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="chart-line-draw" />
      {coords.slice(-6).map((c, i) => (
        <circle key={i} cx={c.x} cy={c.y} r="3" fill={color} className="chart-dot" />
      ))}
      {coords.map((c, i) => (
        <text key={i} x={c.x} y={H - 2} textAnchor="middle" className="chart-label">
          {points[i].label.slice(5)}
        </text>
      ))}
    </svg>
  );
}

function TrendModule({ data }: { data: DashboardData }) {
  const attPoints = data.attendance_trend.map((p) => ({ label: p.date_val, value: p.rate }));
  const scorePoints = data.score_trend.map((p) => ({ label: p.date_val, value: p.avg_rate }));
  return (
    <section className="dash-module">
      <div className="dash-module-head">
        <div>
          <h3>趋势分析</h3>
          <p>出勤与成绩变化</p>
        </div>
        <TrendingUp className="dash-module-icon" />
      </div>
      <div className="trend-charts">
        <div className="trend-chart-block">
          <div className="trend-chart-title"><span className="legend-dot dot-green" />出勤率趋势</div>
          <LineChart points={attPoints} color="#8fc7ad" />
        </div>
        <div className="trend-chart-block">
          <div className="trend-chart-title"><span className="legend-dot dot-orange" />得分率趋势</div>
          <LineChart points={scorePoints} color="#e4b863" />
        </div>
      </div>
    </section>
  );
}

function CourseHealthModule({ health }: { health: CourseHealthItem[] }) {
  const top = health.slice(0, 8);
  return (
    <section className="dash-module">
      <div className="dash-module-head">
        <div>
          <h3>课程健康度</h3>
          <p>综合出勤、成绩、满员率与教师负载</p>
        </div>
        <Activity className="dash-module-icon" />
      </div>
      <div className="health-list">
        {top.length === 0 && <div className="chart-empty">暂无课程数据</div>}
        {top.map((h) => (
          <div key={h.course_id} className="health-row">
            <div className="health-row-head">
              <div className="health-name">
                <span className={`risk-dot risk-${h.risk_level}`} />
                <div>
                  <strong>{h.name}</strong>
                  <p>{h.subject} · {h.teacher} · {DAY_NAMES[h.day]} {TIME_SLOTS[h.slot - 1]}</p>
                </div>
              </div>
              <b>{h.health_score}</b>
            </div>
            <div className="progress-track"><div className={`fill-${h.health_score >= 80 ? "good" : h.health_score >= 65 ? "mid" : "low"}`} style={{ width: `${h.health_score}%` }} /></div>
            <div className="health-meta">
              <span>出勤 {h.attendance_rate}%</span>
              <span>成绩 {h.score_rate}%</span>
              <span>满员 {h.utilization}%</span>
              {h.trend_delta !== 0 && (
                <span className={h.trend_delta > 0 ? "trend-up" : "trend-down"}>
                  {h.trend_delta > 0 ? <TrendingUp /> : <TrendingDown />} {Math.abs(h.trend_delta)}pp
                </span>
              )}
            </div>
            {h.signals.length > 0 && (
              <div className="signal-row">{h.signals.slice(0, 3).map((s) => <span key={s} className="signal-chip">{s}</span>)}</div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function RiskModule({ risk }: { risk: RiskStudentItem[] }) {
  const top = risk.slice(0, 6);
  return (
    <section className="dash-module">
      <div className="dash-module-head">
        <div>
          <h3>学生风险榜</h3>
          <p>出勤、成绩与近期缺勤综合评分</p>
        </div>
        <AlertTriangle className="dash-module-icon" />
      </div>
      <div className="risk-list">
        {top.length === 0 && <div className="chart-empty">暂无学生数据</div>}
        {top.map((r) => (
          <div key={r.student_id} className="risk-row">
            <div
              className="risk-ring"
              style={{ "--risk": `${Math.min(99, r.risk_score) * 3.6}deg` } as CSSProperties}
            >
              <span>{r.risk_score}</span>
            </div>
            <div className="risk-body">
              <div className="risk-name">
                <strong>{r.name}</strong>
                <span className={`risk-badge risk-${r.risk_level}`}>
                  {r.risk_level === "high" ? "高危" : r.risk_level === "medium" ? "关注" : "稳定"}
                </span>
              </div>
              <p>{r.grade_level}{r.grade} · 出勤{r.attendance_rate}% · 成绩{r.score_rate}% · {r.courses}门课</p>
              <div className="signal-row">
                {r.signals.slice(0, 3).map((s) => <span key={s} className="signal-chip">{s}</span>)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function AiDashboardPanel({ setError }: { setError: (e: string) => void }) {
  const [type, setType] = useState("overview");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AiInsightResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [aiError, setAiError] = useState("");
  const quick = [
    { id: "overview", label: "机构体检" },
    { id: "risk", label: "风险预警" },
    { id: "schedule", label: "排课优化" },
  ];
  const run = async (insightType: string, q = "") => {
    setLoading(true);
    setAiError("");
    setResult(null);
    try {
      setResult(await api.analysis.aiInsight({ insight_type: insightType, question: q || undefined }));
    } catch (e: any) {
      setAiError(e.message || "AI 洞察生成失败");
      setError(e.message || "AI 洞察生成失败");
    } finally {
      setLoading(false);
    }
  };
  return (
    <section className="dash-module dash-ai-module">
      <div className="dash-module-head">
        <div>
          <h3>AI 教学洞察</h3>
          <p>用自然语言让 AI 分析机构运营、课程与风险</p>
        </div>
        <Sparkles className="dash-module-icon" />
      </div>
      <div className="ai-quick-row">
        {quick.map((q) => (
          <button key={q.id} className={`chip ${type === q.id ? "active" : ""}`} onClick={() => { setType(q.id); run(q.id); }}>
            {q.label}
          </button>
        ))}
      </div>
      <div className="ai-question-row">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && question.trim()) { setType("qa"); run("qa", question.trim()); } }}
          placeholder="输入问题，如：哪些课程最需要优化？"
          className="field"
        />
        <button className="primary-btn" disabled={loading || !question.trim()} onClick={() => run("qa", question.trim())}>
          <Sparkles className="w-4 h-4" /> {loading ? "分析中..." : "提问"}
        </button>
      </div>
      {loading && <div className="report-loading">AI 正在分析机构数据...</div>}
      {aiError && <div className="test-error px-3 py-2 rounded-2xl text-sm">{aiError}</div>}
      {result && !loading && (
        <div className="report-sheet ai-result-sheet">
          <ReportContent text={result.answer} />
          <div className="report-meta">模型: {result.model} · 生成时间: {result.generated_at}</div>
        </div>
      )}
    </section>
  );
}

export function DashboardView({ setError }: { setError: (e: string) => void }) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [health, setHealth] = useState<CourseHealthItem[]>([]);
  const [risk, setRisk] = useState<RiskStudentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [seedMsg, setSeedMsg] = useState("");
  const load = async () => {
    setLoading(true);
    try {
      const [d, h, r] = await Promise.all([api.analysis.dashboard(), api.analysis.courseHealth(), api.analysis.risk()]);
      setData(d);
      setHealth(h);
      setRisk(r);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);
  const seed = async () => {
    setSeeding(true);
    setSeedMsg("");
    try {
      const res = await api.demo.reset();
      setSeedMsg(`已重置并生成：${res.students} 名学生、${res.teachers} 名教师、${res.courses} 门课程、${res.attendance} 条考勤、${res.scores} 条成绩`);
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSeeding(false);
    }
  };
  return (
    <div className="view-page p-6 dashboard-page">
      <div className="dashboard-head">
        <div>
          <h2>教学驾驶舱</h2>
          <p>{data?.today_date || ""} · 机构运营、课堂与 AI 洞察一站式掌握</p>
        </div>
        <button onClick={load} disabled={loading} className="ghost-btn">
          <RefreshCw className={`w-4 h-4 ${loading ? "spin-slow" : ""}`} /> {loading ? "加载中..." : "刷新"}
        </button>
      </div>
      {data && data.counts.students === 0 && (
        <div className="warning-banner p-3 flex items-center justify-between gap-3 text-sm mb-4">
          <span>当前数据库为空，可先生成一套演示数据用于查看完整驾驶舱。</span>
          <button onClick={seed} disabled={seeding} className="ghost-btn !px-3 !py-1 text-xs">
            {seeding ? "生成中..." : "生成演示数据"}
          </button>
        </div>
      )}
      {seedMsg && <div className="test-ok px-3 py-2 rounded-2xl text-sm mb-3">{seedMsg}</div>}
      {loading && <div className="dash-loading">正在汇总教学数据...</div>}
      {!loading && data && (
        <>
          <KpiGrid data={data} />
          <div className="dash-grid dash-grid-main mt-4">
            <TodayModule data={data} />
            <WeeklyModule data={data} />
          </div>
          <div className="dash-grid dash-grid-secondary mt-4">
            <SubjectModule data={data} />
            <TrendModule data={data} />
          </div>
          <div className="dash-grid dash-grid-secondary mt-4">
            <CourseHealthModule health={health} />
            <RiskModule risk={risk} />
          </div>
          <div className="mt-4">
            <AiDashboardPanel setError={setError} />
          </div>
        </>
      )}
    </div>
  );
}
