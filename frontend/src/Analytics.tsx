import { useState, useEffect, useRef, useCallback, type FormEvent } from "react";
import { FileText, Settings, Zap, Download } from "lucide-react";
import { api } from "./api";
import { Modal } from "./Modal";
import type { Student, Subject, Course, ScoreRecord, ScoreForm, ScoreAnalysis, RadarData, SettingsData, AiReport, AdmissionLine, RoadmapData, AiInsightResult } from "./types";
import { EXAM_TYPE_LABELS } from "./types";

// === Searchable student picker ===
export function StudentPicker({ students, value, onChange, placeholder }: {
  students: Student[]; value: number; onChange: (id: number) => void; placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const selected = students.find(s => s.id === value);
  const filtered = query ? students.filter(s => s.name.includes(query) || s.grade.includes(query) || s.grade_level.includes(query)) : students;
  return (
    <div className="relative" onBlur={e => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setOpen(false); }}>
      <input
        value={open ? query : (query || (selected ? `${selected.name}（${selected.grade}）` : ""))}
        onFocus={() => { setOpen(true); setQuery(""); }}
        onChange={e => { setQuery(e.target.value); setOpen(true); }}
        placeholder={placeholder || "输入姓名搜索学生..."}
        className="field"
      />
      {open && (
        <div className="absolute z-30 w-full picker-dropdown max-h-48 overflow-auto mt-1">
          {filtered.map(s => (
            <button key={s.id} type="button" onClick={() => { onChange(s.id); setOpen(false); setQuery(""); }}
              className="w-full text-left px-3 py-1.5 text-xs text-white/90 hover:bg-white/10 transition-colors">
              {s.name} <span className="text-white/55">（{s.grade_level}{s.grade}）</span>
            </button>
          ))}
          {filtered.length === 0 && <div className="px-3 py-2 text-xs text-white/50">无匹配学生</div>}
        </div>
      )}
    </div>
  );
}

// === Radar Chart SVG ===
export function RadarChart({ axes }: { axes: RadarData["axes"] }) {
  if (axes.length < 3) return <div className="text-xs text-slate-400 py-8 text-center">数据不足，无法生成雷达图（至少需要3个学科）</div>;
  const cx = 140, cy = 140, r = 110, levels = 5;
  const angles = axes.map((_, i) => (Math.PI * 2 * i) / axes.length - Math.PI / 2);
  const scale = (v: number) => (v / 100) * r;
  const pts = (fn: (a: RadarData["axes"][0]) => number) =>
    angles.map((an, i) => { const d = scale(fn(axes[i])); return `${cx + d * Math.cos(an)},${cy + d * Math.sin(an)}`; });
  return (
    <div className="flex flex-col items-center">
      <div className="radar-wrap">
      <svg viewBox="0 0 280 280" className="w-full h-full">
        {Array.from({ length: levels }, (_, i) => r * ((i + 1) / levels)).map((gr, i) => <circle key={i} className="radar-grid-ring" style={{animationDelay: `${0.1 + i * 0.09}s`}} cx={cx} cy={cy} r={gr} fill="none" stroke="rgba(100,116,139,0.42)" strokeWidth="1" />)}
        {angles.map((an, i) => <line key={i} className="radar-axis-line" style={{animationDelay: `${0.18 + i * 0.05}s`}} x1={cx} y1={cy} x2={cx + r * Math.cos(an)} y2={cy + r * Math.sin(an)} stroke="rgba(100,116,139,0.34)" strokeWidth="1" />)}
        <polygon className="radar-polygon" points={pts(a => a.overall_avg_rate || 0).join(" ")} fill="rgba(99,102,241,0.15)" stroke="#6366f1" strokeWidth="1.5" />
        <polygon className="radar-polygon radar-polygon-late" points={pts(a => a.entry_avg_rate || 0).join(" ")} fill="rgba(251,146,60,0.12)" stroke="#f97316" strokeWidth="1.3" strokeDasharray="5 3" />
        <polygon className="radar-polygon radar-polygon-later" points={pts(a => a.quiz_avg_rate || 0).join(" ")} fill="rgba(34,197,94,0.1)" stroke="#22c55e" strokeWidth="1.2" strokeDasharray="4 2" />
        {axes.map((a, i) => <text key={i} className="radar-label fill-slate-600" style={{animationDelay: `${0.55 + i * 0.08}s`}} x={cx + (r + 18) * Math.cos(angles[i])} y={cy + (r + 18) * Math.sin(angles[i])} textAnchor="middle" dominantBaseline="middle" fontSize="11" fontFamily="system-ui">{a.subject}</text>)}
      </svg>
      </div>
      <div className="radar-legend">
        <span className="flex items-center gap-1"><span className="legend-dot dot-orange" />课前诊断</span>
        <span className="flex items-center gap-1"><span className="legend-dot dot-green" />课后测验</span>
        <span className="flex items-center gap-1"><span className="legend-dot dot-line" />综合</span>
      </div>
    </div>
  );
}

// === Analysis View ===
export function AnalysisView({ students, setError }: {
  students: Student[]; setError: (e: string) => void;
}) {
  const [subTab, setSubTab] = useState("scores");
  const [selectedStudent, setSelectedStudent] = useState(students[0]?.id || 0);
  const [studentSearch, setStudentSearch] = useState("");
  const [stuGradeLevel, setStuGradeLevel] = useState("");
  const [stuGrade, setStuGrade] = useState("");
  const [scoreData, setScoreData] = useState<ScoreAnalysis | null>(null);
  const [radarData, setRadarData] = useState<RadarData | null>(null);
  const [roadmapData, setRoadmapData] = useState<RoadmapData | null>(null);
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const radarSeq = useRef(0);
  useEffect(() => { if (subTab === "scores") loadScore(); if (subTab === "radar") loadRadar(); if (subTab === "roadmap") loadRoadmap(); }, [subTab, selectedStudent]);
  const loadScore = async () => { setLoading(true); setScoreData(null); try { setScoreData(await api.analysis.scores({ student_id: selectedStudent || undefined })); } catch(e:any){setError(e.message)} finally{setLoading(false)} };
  const loadRadar = async () => { if(!selectedStudent)return; const seq = ++radarSeq.current; setLoading(true); setRadarData(null); try { const data = await api.analysis.radar(selectedStudent); if (seq === radarSeq.current) setRadarData(data); } catch(e:any){ if (seq === radarSeq.current) setError(e.message); } finally{ if (seq === radarSeq.current) setLoading(false); } };
  const loadRoadmap = async () => { if(!selectedStudent)return; setLoading(true); setRoadmapData(null); try { setRoadmapData(await api.analysis.roadmap(selectedStudent)); } catch(e:any){setError(e.message)} finally{setLoading(false)} };
  const tabs = [ { id: "scores", label: "成绩分析" }, { id: "radar", label: "个人雷达" }, { id: "roadmap", label: "择校冲刺" }, { id: "ai", label: "AI 报告" } ];
  return (
    <div className="view-page p-6">
      <div className="flex justify-between mb-4"><h2 className="text-base font-semibold text-gray-800">数据分析</h2><button onClick={()=>setShowSettings(true)} className="ghost-btn !px-2 !py-1 text-xs"><Settings className="w-3.5 h-3.5" /> API设置</button></div>
      <div className="flex gap-2 mb-4">{tabs.map(t=><button key={t.id} onClick={()=>setSubTab(t.id)} className={`chip ${subTab===t.id?"active":""}`}>{t.label}</button>)}</div>
      {subTab==="scores" && <select value={selectedStudent} onChange={e=>setSelectedStudent(+e.target.value)} className="field field-auto min-w-[120px] mb-3"><option value={0}>全部学生</option>{students.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select>}
      {(subTab==="scores"||subTab==="radar"||subTab==="roadmap"||subTab==="ai") && (
        <div className="flex gap-2 mb-3 flex-wrap items-center">
          <input value={studentSearch} onChange={e=>setStudentSearch(e.target.value)} placeholder="搜索学生..." className="field field-auto min-w-[140px]" />
          <select value={stuGradeLevel} onChange={e=>{setStuGradeLevel(e.target.value);setStuGrade("")}} className="field field-auto"><option value="">全部学段</option><option value="初中">初中</option><option value="高中">高中</option></select>
          {stuGradeLevel && <select value={stuGrade} onChange={e=>setStuGrade(e.target.value)} className="field field-auto"><option value="">全部年级</option>{(stuGradeLevel==="初中"?["初一","初二","初三"]:["高一","高二","高三"]).map(g=><option key={g} value={g}>{g}</option>)}</select>}
          {studentSearch||stuGradeLevel&&(<span className="text-[10px] text-slate-400">{(()=>{const f=students.filter(s=>(!studentSearch||s.name.includes(studentSearch))&&(!stuGradeLevel||s.grade_level===stuGradeLevel)&&(!stuGrade||s.grade===stuGrade));return `${f.length}人`})()}</span>)}
        </div>
      )}
      {loading && <div className="text-sm text-slate-400 py-8 text-center">加载中...</div>}
      {!loading && subTab==="scores" && scoreData && <ScorePanel data={scoreData} />}
      {subTab==="radar" && <RadarPanel students={(studentSearch||stuGradeLevel)?students.filter(s=>(!studentSearch||s.name.includes(studentSearch))&&(!stuGradeLevel||s.grade_level===stuGradeLevel)&&(!stuGrade||s.grade===stuGrade)):students} radarData={radarData} selectedStudent={selectedStudent} setSelectedStudent={setSelectedStudent} loading={loading} />}
      {subTab==="roadmap" && <RoadmapPanel students={(studentSearch||stuGradeLevel)?students.filter(s=>(!studentSearch||s.name.includes(studentSearch))&&(!stuGradeLevel||s.grade_level===stuGradeLevel)&&(!stuGrade||s.grade===stuGrade)):students} roadmapData={roadmapData} selectedStudent={selectedStudent} setSelectedStudent={setSelectedStudent} loading={loading} setError={setError} />}
      {!loading && subTab==="ai" && <AIPanel students={(studentSearch||stuGradeLevel)?students.filter(s=>(!studentSearch||s.name.includes(studentSearch))&&(!stuGradeLevel||s.grade_level===stuGradeLevel)&&(!stuGrade||s.grade===stuGrade)):students} setError={setError} showSettings={showSettings} setShowSettings={setShowSettings} />}
    </div>
  );
}

function ScorePanel({ data }: { data: ScoreAnalysis }) {
  return <div className="space-y-4">
    <div className="grid grid-cols-5 gap-3">
      {[{l:"总记录",v:data.summary.total,c:"text-slate-700"},{l:"平均得分率",v:data.summary.avg_rate+"%",c:"text-indigo-600"},{l:"最高分率",v:data.summary.best_rate+"%",c:"text-green-600"},{l:"最低分率",v:data.summary.lowest_rate+"%",c:"text-red-500"},{l:"学校/测验/入班",v:`${data.summary.school_count}/${data.summary.quiz_count}/${data.summary.entry_count}`,c:"text-slate-600"}].map(x=><div key={x.l} className="stat-tile p-3 text-center"><div className="text-xs text-slate-400">{x.l}</div><div className={`text-lg font-bold ${x.c}`}>{x.v}</div></div>)}
    </div>
    <div className="table-panel"><div className="px-4 py-2 table-head border-b text-xs font-medium text-slate-400">分科目成绩统计</div>
      {data.by_subject.map(s=><div key={s.subject_id} className="flex items-center justify-between px-4 py-2 border-b last:border-0 text-sm"><span className="text-white/90 w-16">{s.subject.name}</span><div className="flex items-center gap-3 flex-1 ml-4"><div className="w-full max-w-xs h-2 progress-track"><div className={`h-full rounded-full ${s.avg_rate>=80?"fill-good":s.avg_rate>=60?"fill-mid":"fill-low"}`} style={{width:`${s.avg_rate}%`}}/></div><span className="text-xs font-medium text-white/75 w-12 text-right">{s.avg_rate}%</span><span className="text-[10px] text-white/50 w-16 text-right">{s.total}次</span></div></div>)}
    </div>
  </div>;
}

function RadarPanel({ students, radarData, selectedStudent, setSelectedStudent, loading }: {
  students: Student[]; radarData: RadarData|null; selectedStudent: number; setSelectedStudent: (v:number)=>void; loading: boolean;
}) {
  return <div className="space-y-4">
    <div className="max-w-[220px]"><StudentPicker students={students} value={selectedStudent} onChange={setSelectedStudent} /></div>
    {loading && <div className="text-sm text-slate-400 py-8 text-center">加载中...</div>}
    {radarData && <div className="panel p-4 flex flex-col items-center"><h3 className="text-sm font-semibold text-slate-800 mb-1">{radarData.student.name} ({radarData.student.grade})</h3><RadarChart axes={radarData.axes} /><div className="mt-3 w-full max-w-lg space-y-1">{radarData.axes.map(a=><div key={a.subject_id} className="flex items-center gap-2 text-xs"><span className="w-12 text-slate-600 font-medium">{a.subject}</span><span className="text-orange-600">课前{a.entry_avg_rate}%</span><span className="text-green-600">课后{a.quiz_avg_rate}%</span><span className={`font-medium w-14 text-right ${a.quiz_avg_rate-a.entry_avg_rate>=0?"text-green-600":"text-red-500"}`}>{(a.quiz_avg_rate-a.entry_avg_rate>=0?"+":"")+(a.quiz_avg_rate-a.entry_avg_rate).toFixed(1)}pp</span><span className="text-slate-400 ml-auto">出勤{a.attendance_rate}% · {a.record_count}条</span></div>)}</div></div>}
  </div>;
}

// === 择校冲刺分析 ===
function RoadmapPanel({ students, roadmapData, selectedStudent, setSelectedStudent, loading, setError }: {
  students: Student[]; roadmapData: RoadmapData|null; selectedStudent: number;
  setSelectedStudent: (v:number)=>void; loading: boolean; setError: (e:string)=>void;
}) {
  const [lines, setLines] = useState<AdmissionLine[]>([]);
  const [filterExam, setFilterExam] = useState("");
  const [filterRegion, setFilterRegion] = useState("");
  const [showLineForm, setShowLineForm] = useState(false);
  const [aiReport, setAiReport] = useState<AiInsightResult | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState("");

  const loadLines = useCallback(() => {
    api.analysis.admissionLines({ exam_type: filterExam || undefined, region: filterRegion || undefined })
      .then(setLines).catch(e => setError(e.message));
  }, [filterExam, filterRegion, setError]);
  useEffect(() => { loadLines(); }, [loadLines]);

  const genAi = async () => {
    if (!selectedStudent) return;
    setAiLoading(true); setAiError(""); setAiReport(null);
    try { setAiReport(await api.analysis.aiRoadmap(selectedStudent)); }
    catch (e: any) { const msg = e.message || "生成失败"; setAiError(msg); setError(msg); }
    finally { setAiLoading(false); }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <div className="max-w-[240px]"><StudentPicker students={students} value={selectedStudent} onChange={(id) => { setSelectedStudent(id); setAiReport(null); }} /></div>
        <span className="text-xs text-slate-400">选择学生后自动生成中考/高考择校冲刺分析</span>
      </div>
      {loading && <div className="text-sm text-slate-400 py-8 text-center">加载中...</div>}
      {roadmapData && (
        <>
          <div className="panel p-4">
            <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-800">{roadmapData.student.name} · {roadmapData.student.grade}{roadmapData.student.track ? `（${roadmapData.student.track}）` : ""}</h3>
                <div className="text-xs text-slate-400">{roadmapData.stage.stage} · {EXAM_TYPE_LABELS[roadmapData.stage.exam_type] || roadmapData.stage.exam_type}（{roadmapData.stage.region}）</div>
              </div>
              <button onClick={genAi} disabled={aiLoading} className="primary-btn !px-3 !py-1.5 text-xs"><Zap className="w-3.5 h-3.5" /> {aiLoading ? "生成中..." : "生成 AI 冲刺报告"}</button>
            </div>
            <div className="grid grid-cols-3 gap-3 mb-3">
              <div className="stat-tile p-3 text-center"><div className="text-xs text-slate-400">当前估算总分</div><div className="text-lg font-bold text-indigo-600">{roadmapData.stage.current_total}<span className="text-xs text-slate-400">/{roadmapData.stage.total_full}</span></div></div>
              <div className="stat-tile p-3 text-center"><div className="text-xs text-slate-400">预计可达</div><div className="text-lg font-bold text-green-600">{roadmapData.stage.projected_total}<span className="text-xs text-slate-400">/{roadmapData.stage.total_full}</span></div></div>
              <div className="stat-tile p-3 text-center"><div className="text-xs text-slate-400">位次参考</div><div className="text-sm font-bold text-slate-700 pt-1.5">{roadmapData.stage.rank_hint || "—"}</div></div>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">{roadmapData.summary}</p>
          </div>

          <div className="panel p-4">
            <h4 className="text-xs font-semibold text-slate-700 mb-2">目标学校（稳妥 ≥ +8 分 / 冲刺 -12~+8 分 / 差距 &lt; -12 分）</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {roadmapData.targets.slice(0, 8).map((t, i) => (
                <div key={i} className="flex items-center justify-between px-3 py-2 rounded-2xl bg-white/50 border border-slate-100 text-xs">
                  <div>
                    <div className="font-medium text-slate-800">{t.school}</div>
                    <div className="text-[10px] text-slate-400">{t.category}{t.track ? ` / ${t.track}` : ""}{t.province === "江苏" ? " / 江苏" : ""} · 线 {t.line_score} 分</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`status-chip px-1.5 py-0.5 text-[10px] ${t.status === "稳妥" ? "status-school" : t.status === "冲刺" ? "status-class" : "status-quiz"}`}>{t.status}</span>
                    <span className={`font-medium ${t.gap >= 0 ? "text-green-600" : "text-red-500"}`}>{t.gap >= 0 ? "+" : ""}{t.gap}</span>
                  </div>
                </div>
              ))}
              {roadmapData.targets.length === 0 && <div className="text-xs text-slate-400 py-4 text-center col-span-2">暂无目标学校，请先维护分数线</div>}
            </div>
          </div>

          <div className="panel p-4">
            <h4 className="text-xs font-semibold text-slate-700 mb-2">分科提分空间（按可提分排序）</h4>
            <div className="space-y-1.5">
              {roadmapData.subjects.slice(0, 8).map((x) => (
                <div key={x.subject_id} className="flex items-center gap-2 text-xs">
                  <span className="w-12 text-slate-600 font-medium">{x.subject}</span>
                  <div className="w-full max-w-xs h-2 progress-track"><div className={`h-full rounded-full ${x.level === "优势" ? "fill-good" : x.level === "中等" ? "fill-mid" : "fill-low"}`} style={{ width: `${Math.min(100, x.latest_rate)}%` }} /></div>
                  <span className="w-14 text-right text-slate-500">{x.latest_rate}%</span>
                  {x.gain_potential > 0 && <span className="w-20 text-right text-amber-600">可提 {x.gain_potential} 分</span>}
                  <span className="text-slate-400 ml-auto truncate">{x.advice}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="panel p-4">
            <h4 className="text-xs font-semibold text-slate-700 mb-2">阶段学习建议</h4>
            <ul className="space-y-1 text-xs text-slate-600">
              {roadmapData.suggestions.map((s, i) => <li key={i} className="flex gap-2"><span className="text-indigo-400">•</span>{s}</li>)}
            </ul>
          </div>

          {aiError && <div className="test-error px-3 py-2 rounded-2xl text-sm">{aiError}</div>}
          {aiLoading && <div className="report-loading">正在调用 AI 生成冲刺报告...</div>}
          {aiReport && !aiLoading && aiReport.answer.trim() && (
            <div className="report-sheet report-reveal max-h-[520px] overflow-auto">
              <ReportContent text={aiReport.answer} />
              <div className="report-meta">模型: {aiReport.model} · 生成时间: {aiReport.generated_at}</div>
            </div>
          )}
        </>
      )}
      {!loading && !roadmapData && <div className="panel p-6 text-center text-sm text-slate-400">选择学生后查看择校冲刺分析</div>}

      <LineManager
        lines={lines} onChanged={loadLines}
        filterExam={filterExam} setFilterExam={setFilterExam}
        filterRegion={filterRegion} setFilterRegion={setFilterRegion}
        showForm={showLineForm} setShowForm={setShowLineForm}
        setError={setError}
      />
    </div>
  );
}

function LineManager({ lines, onChanged, filterExam, setFilterExam, filterRegion, setFilterRegion, showForm, setShowForm, setError }: {
  lines: AdmissionLine[]; onChanged: () => void;
  filterExam: string; setFilterExam: (v: string) => void;
  filterRegion: string; setFilterRegion: (v: string) => void;
  showForm: boolean; setShowForm: (v: boolean) => void;
  setError: (e: string) => void;
}) {
  return (
    <div className="panel p-4">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h4 className="text-xs font-semibold text-slate-700">中考/高考分数线库（2026 苏州·江苏）</h4>
        <div className="flex gap-2 items-center">
          <select value={filterExam} onChange={e => setFilterExam(e.target.value)} className="field field-auto min-w-[90px] !py-1 text-xs">
            <option value="">全部考试</option>
            {Object.entries(EXAM_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <select value={filterRegion} onChange={e => setFilterRegion(e.target.value)} className="field field-auto min-w-[80px] !py-1 text-xs">
            <option value="">全部地区</option>
            <option value="苏州">苏州</option>
            <option value="江苏">江苏</option>
          </select>
          <button onClick={() => setShowForm(true)} className="ghost-btn !px-2 !py-1 text-xs">+ 添加分数线</button>
        </div>
      </div>
      <div className="max-h-56 overflow-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-slate-400 border-b border-slate-100">
              <th className="py-1.5 pr-2 font-medium">考试</th>
              <th className="py-1.5 pr-2 font-medium">地区</th>
              <th className="py-1.5 pr-2 font-medium">年份</th>
              <th className="py-1.5 pr-2 font-medium">批次</th>
              <th className="py-1.5 pr-2 font-medium">类别</th>
              <th className="py-1.5 pr-2 font-medium">省份</th>
              <th className="py-1.5 pr-2 font-medium">学校/线</th>
              <th className="py-1.5 pr-2 font-medium text-right">最低分</th>
              <th className="py-1.5 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {lines.map(l => (
              <tr key={l.id} className="border-b border-slate-50 text-slate-600">
                <td className="py-1.5 pr-2">{EXAM_TYPE_LABELS[l.exam_type] || l.exam_type}</td>
                <td className="py-1.5 pr-2">{l.region}</td>
                <td className="py-1.5 pr-2">{l.year}</td>
                <td className="py-1.5 pr-2">{l.category}</td>
                <td className="py-1.5 pr-2">{l.track || "—"}</td>
                <td className="py-1.5 pr-2">{l.province || "—"}</td>
                <td className="py-1.5 pr-2 text-slate-800">{l.school}</td>
                <td className="py-1.5 pr-2 text-right font-medium">{l.score}</td>
                <td className="py-1.5 text-right">
                  <button onClick={async () => { try { await api.analysis.deleteAdmissionLine(l.id); onChanged(); } catch (e: any) { setError(e.message); } }} className="icon-btn">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                  </button>
                </td>
              </tr>
            ))}
            {lines.length === 0 && <tr><td colSpan={9} className="py-4 text-center text-slate-400">暂无分数线记录</td></tr>}
          </tbody>
        </table>
      </div>
      {showForm && <LineFormModal onClose={() => setShowForm(false)} onSaved={() => { setShowForm(false); onChanged(); }} setError={setError} />}
    </div>
  );
}

function LineFormModal({ onClose, onSaved, setError }: {
  onClose: () => void; onSaved: () => void; setError: (e: string) => void;
}) {
  const [examType, setExamType] = useState("zhongkao");
  const [region, setRegion] = useState("苏州");
  const [year, setYear] = useState(2026);
  const [category, setCategory] = useState("四星级高中");
  const [track, setTrack] = useState("");
  const [province, setProvince] = useState("");
  const [school, setSchool] = useState("");
  const [code, setCode] = useState("");
  const [score, setScore] = useState(0);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  const handle = async (e: FormEvent) => {
    e.preventDefault(); setSaving(true);
    try {
      await api.analysis.createAdmissionLine({
        exam_type: examType, region, year, category, track, province,
        school, code, score, note,
      });
      onSaved();
    } catch (e: any) { setError(e.message); }
    finally { setSaving(false); }
  };

  return (
    <Modal onClose={onClose}>
      <div className="modal-card w-[440px] max-h-[85vh]">
        <div className="flex justify-between px-5 py-4 border-b">
          <h3 className="font-semibold text-slate-800">添加分数线</h3>
          <button onClick={onClose} className="hover:rotate-90 transition-transform duration-200">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <form onSubmit={handle} className="p-5 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">考试</label>
              <select value={examType} onChange={e => { setExamType(e.target.value); if (e.target.value === "zhongkao") { setRegion("苏州"); } else { setRegion("江苏"); } }} className="field">
                {Object.entries(EXAM_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">地区</label>
              <select value={region} onChange={e => setRegion(e.target.value)} className="field">
                <option value="苏州">苏州</option>
                <option value="江苏">江苏</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">年份</label>
              <input type="number" value={year} onChange={e => setYear(+e.target.value)} className="field" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">批次/类别</label>
              <input value={category} onChange={e => setCategory(e.target.value)} className="field" placeholder="如：四星级高中 / 本科批投档线" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">科类（高考）</label>
              <select value={track} onChange={e => setTrack(e.target.value)} className="field">
                <option value="">—</option>
                <option value="历史类">历史类</option>
                <option value="物理类">物理类</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">学校所在省份（江苏院校在分数接近时优先推荐）</label>
            <input value={province} onChange={e => setProvince(e.target.value)} className="field" placeholder="如：江苏 / 北京 / 上海" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">学校/分数线名称</label>
            <input value={school} onChange={e => setSchool(e.target.value)} required className="field" placeholder="如：江苏省苏州中学校" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">学校代码</label>
              <input value={code} onChange={e => setCode(e.target.value)} className="field" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">最低分</label>
              <input type="number" value={score} onChange={e => setScore(+e.target.value)} min={0} required className="field" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">备注</label>
            <input value={note} onChange={e => setNote(e.target.value)} className="field" />
          </div>
          <button type="submit" disabled={saving} className="primary-btn w-full">{saving ? "保存中..." : "保存"}</button>
        </form>
      </div>
    </Modal>
  );
}

function AIPanel({ students, setError, showSettings, setShowSettings }: {
  students: Student[]; setError: (e:string)=>void; showSettings: boolean; setShowSettings: (v:boolean)=>void;
}) {
  const [studentId, setStudentId] = useState(students[0]?.id||0);
  const [report, setReport] = useState<AiReport|null>(null);
  const [loading, setLoading] = useState(false);
  const [aiError, setAiError] = useState("");
  const [settings, setSettings] = useState<SettingsData|null>(null);
  useEffect(()=>{api.settings.get().then(setSettings).catch(()=>{})},[showSettings]);
  useEffect(()=>{ setAiError(""); if(studentId){ api.analysis.latestAiReport(studentId).then(setReport).catch(()=>setReport(null)); } },[studentId]);
  useEffect(()=>{ if(!loading) return; const timer = setTimeout(()=>{ setLoading(false); setAiError("生成超时，请稍后重试"); }, 130000); return ()=>clearTimeout(timer); }, [loading]);
  const generate = async() => { setLoading(true); setAiError(""); try { setReport(await api.analysis.aiReport(studentId)); } catch(e:any){ const msg = e.message || "生成失败"; setAiError(msg); setError(msg); } finally{ setLoading(false); } };
  const exportPdf = async() => { try { const name = students.find(s=>s.id===studentId)?.name; await api.analysis.aiReportPdf(studentId, name); } catch(e:any){setError(e.message)} };
  return <div className="space-y-4">
    {settings && !settings.deepseek_api_key_set && <div className="warning-banner p-3 flex items-center justify-between text-sm"><span className="text-[#826b3c]">尚未配置 DeepSeek API Key</span><button onClick={()=>setShowSettings(true)} className="ghost-btn !px-2 !py-1 text-xs">立即设置</button></div>}
    <div className="panel controls-panel p-4"><div className="flex items-center gap-3 flex-wrap"><div className="min-w-[200px]"><StudentPicker students={students} value={studentId} onChange={setStudentId} /></div><button onClick={generate} disabled={loading} className="primary-btn"><Zap className="w-4 h-4" /> {loading?"生成中...":"生成新报告"}</button><button onClick={exportPdf} disabled={loading||!report} className="ghost-btn"><Download className="w-4 h-4" /> 导出 PDF</button></div></div>
    {loading && <div className="report-loading">正在调用 DeepSeek 生成报告...</div>}
    {aiError && <div className="test-error px-3 py-2 rounded-2xl text-sm">{aiError}</div>}
    {report && !loading && (report.report?.trim()
      ? <div key={`${studentId}-${report.generated_at}`} className="report-sheet report-reveal max-h-[600px] overflow-auto"><ReportContent text={report.report} /><div className="report-meta">模型: {report.model} · 生成时间: {report.generated_at}</div></div>
      : <div className="test-error px-3 py-2 rounded-2xl text-sm">该报告内容为空，请点击“生成新报告”重新生成</div>)}
    {!report && !loading && <div className="panel p-6 text-center text-sm text-slate-400">暂无报告，选择学生后点击"生成新报告"</div>}
    {showSettings && <SettingsModal settings={settings} onClose={()=>setShowSettings(false)} onSaved={()=>{api.settings.get().then(setSettings).catch(()=>{})}} setError={setError} />}
  </div>;
}

function SettingsModal({ settings, onClose, onSaved, setError }: {
  settings: SettingsData|null; onClose: ()=>void; onSaved: ()=>void; setError: (e:string)=>void;
}) {
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState(settings?.deepseek_model||"deepseek-chat");
  const [baseUrl, setBaseUrl] = useState(settings?.deepseek_base_url||"https://api.deepseek.com");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testMsg, setTestMsg] = useState("");
  const handleSave = async() => { setSaving(true); try { await api.settings.update({ api_key: apiKey||undefined, model, base_url: baseUrl }); onSaved(); onClose(); } catch(e:any){setError(e.message)} finally{setSaving(false)} };
  const handleTest = async() => { setTesting(true); setTestMsg(""); try { await api.settings.test(apiKey||undefined); setTestMsg("连接成功！API Key 有效"); } catch(e:any){setTestMsg("连接失败: "+(e.message||"未知错误"))} finally{setTesting(false)} };
  return (
    <Modal onClose={onClose}>
      <div className="modal-card w-[420px] max-h-[85vh]" onClick={e=>e.stopPropagation()}>
        <div className="flex justify-between px-5 py-4 border-b"><h3 className="font-semibold text-slate-800">DeepSeek API 设置</h3><button onClick={onClose} className="hover:rotate-90 transition-transform duration-200"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div>
        <div className="p-5 space-y-4">
          <div><label className="block text-xs font-medium text-slate-600 mb-1">API Key {settings?.deepseek_api_key_set?<span className="text-green-500 text-[10px]">(已设置: {settings.deepseek_api_key_masked})</span>:""}</label><input value={apiKey} onChange={e=>setApiKey(e.target.value)} type="password" className="field" placeholder={settings?.deepseek_api_key_set?"留空则保持不变":"输入 DeepSeek API Key"} /></div>
          <div><label className="block text-xs font-medium text-slate-600 mb-1">模型</label><input value={model} onChange={e=>setModel(e.target.value)} className="field" /></div>
          <div><label className="block text-xs font-medium text-slate-600 mb-1">API 地址</label><input value={baseUrl} onChange={e=>setBaseUrl(e.target.value)} className="field" /></div>
          {testMsg && <div className={`text-xs px-3 py-2 rounded-2xl ${testMsg.includes("成功")?"test-ok":"test-error"}`}>{testMsg}</div>}
          <div className="flex gap-2"><button onClick={handleTest} disabled={testing} className="ghost-btn flex-1">{testing?"测试中...":"测试连接"}</button><button onClick={handleSave} disabled={saving} className="primary-btn flex-1">{saving?"保存中...":"保存"}</button></div>
        </div>
      </div>
    </Modal>
  );
}

// === Simple markdown renderer ===
export function ReportContent({ text }: { text: string }) {
  const lines = text.split("\n");
  return <>{lines.map((line, i) => {
    const t = line.trim();
    const delay = { animationDelay: `${Math.min(i * 0.04, 0.9)}s` };
    if (!t) return <div key={i} className="h-2 report-line" style={delay} />;
    if (/^#{1,3}\s/.test(t)) { const lv = (t.match(/^(#{1,3})/)![1]).length; const fs = lv===1?"text-base font-bold":lv===2?"text-sm font-semibold":"text-xs font-semibold"; return <div key={i} style={delay} className={`report-line ${fs} text-slate-800 mt-3 mb-1`}>{t.replace(/^#+\s*/, "")}</div>; }
    if (/^[-*]\s/.test(t)) return <div key={i} style={delay} className="report-line text-sm text-slate-600 ml-4">• {t.replace(/^[-*]\s+/, "").replace(/\*\*(.+?)\*\*/g, (_,b)=>b)}</div>;
    return <div key={i} style={delay} className="report-line text-sm text-slate-600 leading-relaxed">{t.replace(/\*\*(.+?)\*\*/g, (_,b)=>b)}</div>;
  })}</>;
}

// === Scores View ===
export function ScoresView({ students, subjects, courses, setError }: {
  students: Student[]; subjects: Subject[]; courses: Course[]; setError: (e: string) => void;
}) {
  const [scores, setScores] = useState<ScoreRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<ScoreRecord | null>(null);
  const [filterStudent, setFilterStudent] = useState(0);
  const [filterSubject, setFilterSubject] = useState(0);
  const [filterType, setFilterType] = useState("");
  useEffect(() => { load(); }, [filterStudent, filterSubject, filterType]);
  const load = () => { setLoading(true); api.scores.list({ student_id: filterStudent||undefined, subject_id: filterSubject||undefined, exam_type: filterType||undefined }).then(setScores).catch(e=>setError(e.message)).finally(()=>setLoading(false)); };
  const exTypes: Record<string,string> = { school_exam: "学校考试", quiz: "小测验", entry_test: "入班诊断" };
  return (
    <div className="view-page p-6">
      <div className="flex justify-between mb-4"><h2 className="text-base font-semibold text-gray-800">成绩管理</h2>
        <button onClick={() => { setEditing(null); setShowForm(true); }} className="primary-btn"><FileText className="w-4 h-4" /> 添加成绩</button>
      </div>
      <div className="flex gap-3 mb-3 flex-wrap">
        <div className="min-w-[150px]"><StudentPicker students={[{id:0,name:"全部学生",grade:"",grade_level:""} as any,...students]} value={filterStudent} onChange={setFilterStudent} placeholder="搜索学生..." /></div>
        <select value={filterSubject} onChange={e=>setFilterSubject(+e.target.value)} className="field field-auto min-w-[100px]"><option value={0}>全部科目</option>{subjects.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select>
        <select value={filterType} onChange={e=>setFilterType(e.target.value)} className="field field-auto min-w-[100px]"><option value="">全部类型</option><option value="school_exam">学校考试</option><option value="quiz">小测验</option></select>
      </div>
      <div className="table-panel">
        <div className="grid grid-cols-[1fr_70px_80px_80px_70px_100px_70px_70px] gap-2 px-4 py-2 table-head border-b text-xs font-medium text-slate-400"><div>学生</div><div>科目</div><div>类型</div><div>考试名称</div><div>得分</div><div>日期</div><div>得分率</div><div></div></div>
        {loading && <div className="text-xs text-slate-400 py-8 text-center">加载中...</div>}
        {!loading && scores.map(r => (
          <div key={r.id} className="grid grid-cols-[1fr_70px_80px_80px_70px_100px_70px_70px] gap-2 px-4 py-2 border-b text-xs items-center hover:bg-white/8 transition-colors">
            <div className="font-medium text-slate-800 truncate">{r.student?.name||"—"}</div><div className="text-slate-500">{r.subject?.name||"—"}</div><div className={`status-chip px-1 py-0.5 text-[10px] ${r.exam_type==="school_exam"?"status-school":"status-quiz"}`}>{exTypes[r.exam_type]||r.exam_type}</div><div className="truncate">{r.exam_name}</div><div className="text-slate-800 font-medium">{r.score}/{r.max_score}</div><div className="text-slate-400">{r.exam_date}</div><div className={`font-medium ${r.rate>=80?"text-green-600":r.rate>=60?"text-amber-600":"text-red-500"}`}>{r.rate}%</div>
            <div className="flex gap-0.5 justify-end"><button onClick={()=>{setEditing(r);setShowForm(true)}} className="icon-btn"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button><button onClick={async()=>{try{await api.scores.delete(r.id);load()}catch(e:any){setError(e.message)}}} className="icon-btn"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></button></div>
          </div>
        ))}
        {!loading && scores.length===0 && <div className="text-xs text-slate-400 py-8 text-center">暂无成绩记录</div>}
      </div>
      {showForm && <ScoreFormModal record={editing} students={students} subjects={subjects} courses={courses} onClose={()=>{setShowForm(false);setEditing(null)}} onSave={()=>{load();setShowForm(false);setEditing(null)}} setError={setError} />}
    </div>
  );
}

function ScoreFormModal({ record, students, subjects, courses, onClose, onSave, setError }: {
  record: ScoreRecord|null; students: Student[]; subjects: Subject[]; courses: Course[]; onClose: ()=>void; onSave: ()=>void; setError: (e:string)=>void;
}) {
  const [studentId, setStudentId] = useState(record?.student_id||0);
  const [subjectId, setSubjectId] = useState(record?.subject_id||subjects[0]?.id||0);
  const [courseId, setCourseId] = useState(record?.course_id||0);
  const [examType, setExamType] = useState(record?.exam_type||"quiz");
  const [examName, setExamName] = useState(record?.exam_name||"");
  const [score, setScore] = useState(record?.score??0);
  const [maxScore, setMaxScore] = useState(record?.max_score??100);
  const [examDate, setExamDate] = useState(record?.exam_date||new Date().toISOString().split("T")[0]);
  const [notes, setNotes] = useState(record?.notes||"");
  const [saving, setSaving] = useState(false);
  const handle = async (e: FormEvent) => { e.preventDefault(); setSaving(true); try { const d: ScoreForm = { student_id: studentId, subject_id: subjectId, course_id: (examType==="quiz"||examType==="entry_test")?courseId||null:null, exam_type: examType, exam_name: examName, score, max_score: maxScore, exam_date: examDate, notes }; if(record) await api.scores.update(record.id,d); else await api.scores.create(d); onSave(); } catch(e:any){setError(e.message)} finally{setSaving(false)} };
  return (
    <Modal onClose={onClose}>
      <div className="modal-card w-[420px] max-h-[85vh]" onClick={e=>e.stopPropagation()}>
        <div className="flex justify-between px-5 py-4 border-b"><h3 className="font-semibold text-slate-800">{record?"编辑成绩":"添加成绩"}</h3><button onClick={onClose} className="hover:rotate-90 transition-transform duration-200"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div>
        <form onSubmit={handle} className="p-5 space-y-3">
          <div><label className="block text-xs font-medium text-slate-600 mb-1">学生</label><StudentPicker students={students} value={studentId} onChange={setStudentId} /></div>
<div className="grid grid-cols-2 gap-3"><div><label className="block text-xs font-medium text-slate-600 mb-1">科目</label><select value={subjectId} onChange={e=>setSubjectId(+e.target.value)} className="field">{subjects.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></div><div><label className="block text-xs font-medium text-slate-600 mb-1">类型</label><div className="flex gap-1 flex-wrap"><button type="button" onClick={()=>{setExamType("school_exam");setCourseId(0)}} className={`chip ${examType==="school_exam"?"active":""}`}>学校考试</button><button type="button" onClick={()=>setExamType("quiz")} className={`chip ${examType==="quiz"?"active":""}`}>补习班测验</button><button type="button" onClick={()=>setExamType("entry_test")} className={`chip ${examType==="entry_test"?"active":""}`}>入班诊断</button></div></div></div>
{(examType==="quiz"||examType==="entry_test") && <div><label className="block text-xs font-medium text-slate-600 mb-1">关联课程</label><select value={courseId} onChange={e=>setCourseId(+e.target.value)} className="field"><option value={0}>—不关联—</option>{courses.filter(c=>c.subject_id===subjectId).map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></div>}
          <div><label className="block text-xs font-medium text-slate-600 mb-1">考试/测验名</label><input value={examName} onChange={e=>setExamName(e.target.value)} required className="field" placeholder="如：期中考试、随堂小测" /></div>
          <div className="grid grid-cols-2 gap-3"><div><label className="block text-xs font-medium text-slate-600 mb-1">得分</label><input type="number" value={score} onChange={e=>setScore(+e.target.value)} min={0} step={0.5} required className="field" /></div><div><label className="block text-xs font-medium text-slate-600 mb-1">满分</label><input type="number" value={maxScore} onChange={e=>setMaxScore(+e.target.value)} min={1} required className="field" /></div></div>
          <div><label className="block text-xs font-medium text-slate-600 mb-1">日期</label><input type="date" value={examDate} onChange={e=>setExamDate(e.target.value)} required className="field" /></div>
          <div><label className="block text-xs font-medium text-slate-600 mb-1">备注</label><input value={notes} onChange={e=>setNotes(e.target.value)} className="field" /></div>
          <button type="submit" disabled={saving||studentId===0} className="primary-btn w-full"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg> {saving?"保存中...":"保存"}</button>
        </form>
      </div>
    </Modal>
  );
}
