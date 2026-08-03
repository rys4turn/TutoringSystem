import { useState, useEffect, useRef, type FormEvent } from "react";
import { FileText, Settings, Zap, Download } from "lucide-react";
import { api } from "./api";
import { Modal } from "./Modal";
import type { Student, Subject, Course, ScoreRecord, ScoreForm, ScoreAnalysis, RadarData, SettingsData, AiReport } from "./types";

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
        value={query || (selected ? `${selected.name}（${selected.grade}）` : "")}
        onFocus={() => { setOpen(true); setQuery(""); }}
        onChange={e => { setQuery(e.target.value); setOpen(true); }}
        placeholder={placeholder || "输入姓名搜索学生..."}
        className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400/50 bg-white/60"
      />
      {open && (
        <div className="absolute z-30 w-full bg-white border border-slate-200 rounded-lg shadow-lg max-h-48 overflow-auto mt-1">
          {filtered.map(s => (
            <button key={s.id} type="button" onClick={() => { onChange(s.id); setOpen(false); setQuery(""); }}
              className="w-full text-left px-3 py-1.5 text-xs hover:bg-indigo-50 transition-colors">
              {s.name} <span className="text-slate-400">（{s.grade_level}{s.grade}）</span>
            </button>
          ))}
          {filtered.length === 0 && <div className="px-3 py-2 text-xs text-slate-400">无匹配学生</div>}
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
      <svg viewBox="0 0 280 280" className="w-72 h-72 animate-radar-in">
        {Array.from({ length: levels }, (_, i) => r * ((i + 1) / levels)).map((gr, i) => <circle key={i} className="radar-fade" style={{animationDelay: `${0.15 + i * 0.08}s`}} cx={cx} cy={cy} r={gr} fill="none" stroke="#e2e8f0" strokeWidth="0.5" />)}
        {angles.map((an, i) => <line key={i} className="radar-fade" style={{animationDelay: `${0.2 + i * 0.04}s`}} x1={cx} y1={cy} x2={cx + r * Math.cos(an)} y2={cy + r * Math.sin(an)} stroke="#e2e8f0" strokeWidth="0.5" />)}
        <polygon className="radar-polygon" points={pts(a => a.overall_avg_rate || 0).join(" ")} fill="rgba(99,102,241,0.15)" stroke="#6366f1" strokeWidth="1.5" />
        <polygon className="radar-polygon radar-polygon-late" points={pts(a => a.entry_avg_rate || 0).join(" ")} fill="rgba(251,146,60,0.12)" stroke="#f97316" strokeWidth="1.3" strokeDasharray="5 3" />
        <polygon className="radar-polygon radar-polygon-later" points={pts(a => a.quiz_avg_rate || 0).join(" ")} fill="rgba(34,197,94,0.1)" stroke="#22c55e" strokeWidth="1.2" strokeDasharray="4 2" />
        {axes.map((a, i) => <text key={i} className="fill-slate-600" style={{animation: "radar-fade 0.5s ease-out both", animationDelay: `${0.6 + i * 0.07}s`}} x={cx + (r + 18) * Math.cos(angles[i])} y={cy + (r + 18) * Math.sin(angles[i])} textAnchor="middle" dominantBaseline="middle" fontSize="11" fontFamily="system-ui">{a.subject}</text>)}
      </svg>
      <div className="flex gap-4 mt-2 text-xs text-slate-500">
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-orange-500/20 border border-orange-500 inline-block" />课前诊断</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500 inline-block" />课后测验</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 inline-block" style={{border: "1.5px dashed #6366f1"}} />综合</span>
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
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const radarSeq = useRef(0);
  useEffect(() => { if (subTab === "scores") loadScore(); if (subTab === "radar") loadRadar(); }, [subTab, selectedStudent]);
  const loadScore = async () => { setLoading(true); setScoreData(null); try { setScoreData(await api.analysis.scores({ student_id: selectedStudent || undefined })); } catch(e:any){setError(e.message)} finally{setLoading(false)} };
  const loadRadar = async () => { if(!selectedStudent)return; const seq = ++radarSeq.current; setLoading(true); setRadarData(null); try { const data = await api.analysis.radar(selectedStudent); if (seq === radarSeq.current) setRadarData(data); } catch(e:any){ if (seq === radarSeq.current) setError(e.message); } finally{ if (seq === radarSeq.current) setLoading(false); } };
  const tabs = [ { id: "scores", label: "成绩分析" }, { id: "radar", label: "个人雷达" }, { id: "ai", label: "AI 报告" } ];
  return (
    <div className="p-6">
      <div className="flex justify-between mb-4"><h2 className="text-base font-semibold text-gray-800">数据分析</h2><button onClick={()=>setShowSettings(true)} className="flex items-center gap-1 px-2 py-1 text-xs text-slate-500 hover:bg-white/50 rounded-lg transition-colors"><Settings className="w-3.5 h-3.5" /> API设置</button></div>
      <div className="flex gap-2 mb-4">{tabs.map(t=><button key={t.id} onClick={()=>setSubTab(t.id)} className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${subTab===t.id?"bg-gradient-to-r from-indigo-500 to-violet-500 text-white shadow-sm":"bg-white/70 border border-slate-200 text-slate-500 hover:bg-white"}`}>{t.label}</button>)}</div>
      {subTab==="scores" && <select value={selectedStudent} onChange={e=>setSelectedStudent(+e.target.value)} className="border rounded-md px-2 py-1 text-xs bg-white/70 focus:outline-none focus:ring-2 focus:ring-indigo-400/50 min-w-[120px] mb-3"><option value={0}>全部学生</option>{students.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select>}
      {(subTab==="scores"||subTab==="radar"||subTab==="ai") && (
        <div className="flex gap-2 mb-3 flex-wrap items-center">
          <input value={studentSearch} onChange={e=>setStudentSearch(e.target.value)} placeholder="搜索学生..." className="border rounded-md px-2 py-1 text-xs bg-white/70 focus:outline-none focus:ring-2 focus:ring-indigo-400/50 min-w-[140px]" />
          <select value={stuGradeLevel} onChange={e=>{setStuGradeLevel(e.target.value);setStuGrade("")}} className="border rounded-md px-2 py-1 text-xs bg-white/70 focus:outline-none focus:ring-2 focus:ring-indigo-400/50"><option value="">全部学段</option><option value="初中">初中</option><option value="高中">高中</option></select>
          {stuGradeLevel && <select value={stuGrade} onChange={e=>setStuGrade(e.target.value)} className="border rounded-md px-2 py-1 text-xs bg-white/70 focus:outline-none focus:ring-2 focus:ring-indigo-400/50"><option value="">全部年级</option>{(stuGradeLevel==="初中"?["初一","初二","初三"]:["高一","高二","高三"]).map(g=><option key={g} value={g}>{g}</option>)}</select>}
          {studentSearch||stuGradeLevel&&(<span className="text-[10px] text-slate-400">{(()=>{const f=students.filter(s=>(!studentSearch||s.name.includes(studentSearch))&&(!stuGradeLevel||s.grade_level===stuGradeLevel)&&(!stuGrade||s.grade===stuGrade));return `${f.length}人`})()}</span>)}
        </div>
      )}
      {loading && <div className="text-sm text-slate-400 py-8 text-center">加载中...</div>}
      {!loading && subTab==="scores" && scoreData && <ScorePanel data={scoreData} />}
      {subTab==="radar" && <RadarPanel students={(studentSearch||stuGradeLevel)?students.filter(s=>(!studentSearch||s.name.includes(studentSearch))&&(!stuGradeLevel||s.grade_level===stuGradeLevel)&&(!stuGrade||s.grade===stuGrade)):students} radarData={radarData} selectedStudent={selectedStudent} setSelectedStudent={setSelectedStudent} loading={loading} />}
      {!loading && subTab==="ai" && <AIPanel students={(studentSearch||stuGradeLevel)?students.filter(s=>(!studentSearch||s.name.includes(studentSearch))&&(!stuGradeLevel||s.grade_level===stuGradeLevel)&&(!stuGrade||s.grade===stuGrade)):students} setError={setError} showSettings={showSettings} setShowSettings={setShowSettings} />}
    </div>
  );
}

function ScorePanel({ data }: { data: ScoreAnalysis }) {
  return <div className="space-y-4">
    <div className="grid grid-cols-5 gap-3">
      {[{l:"总记录",v:data.summary.total,c:"text-slate-700"},{l:"平均得分率",v:data.summary.avg_rate+"%",c:"text-indigo-600"},{l:"最高分率",v:data.summary.best_rate+"%",c:"text-green-600"},{l:"最低分率",v:data.summary.lowest_rate+"%",c:"text-red-500"},{l:"学校/测验/入班",v:`${data.summary.school_count}/${data.summary.quiz_count}/${data.summary.entry_count}`,c:"text-slate-600"}].map(x=><div key={x.l} className="bg-white rounded-lg border p-3 text-center"><div className="text-xs text-slate-400">{x.l}</div><div className={`text-lg font-bold ${x.c}`}>{x.v}</div></div>)}
    </div>
    <div className="bg-white rounded-lg border overflow-hidden"><div className="px-4 py-2 bg-slate-50/80 border-b text-xs font-medium text-slate-400">分科目成绩统计</div>
      {data.by_subject.map(s=><div key={s.subject_id} className="flex items-center justify-between px-4 py-2 border-b last:border-0 text-sm"><span className="text-slate-700 w-16">{s.subject.name}</span><div className="flex items-center gap-3 flex-1 ml-4"><div className="w-full max-w-xs h-2 bg-slate-100 rounded-full overflow-hidden"><div className={`h-full rounded-full ${s.avg_rate>=80?"bg-green-500":s.avg_rate>=60?"bg-amber-500":"bg-red-500"}`} style={{width:`${s.avg_rate}%`}}/></div><span className="text-xs font-medium text-slate-600 w-12 text-right">{s.avg_rate}%</span><span className="text-[10px] text-slate-400 w-16 text-right">{s.total}次</span></div></div>)}
    </div>
  </div>;
}

function RadarPanel({ students, radarData, selectedStudent, setSelectedStudent, loading }: {
  students: Student[]; radarData: RadarData|null; selectedStudent: number; setSelectedStudent: (v:number)=>void; loading: boolean;
}) {
  return <div className="space-y-4">
    <div className="max-w-[220px]"><StudentPicker students={students} value={selectedStudent} onChange={setSelectedStudent} /></div>
    {loading && <div className="text-sm text-slate-400 py-8 text-center">加载中...</div>}
    {radarData && <div className="bg-white rounded-lg border p-4 flex flex-col items-center"><h3 className="text-sm font-semibold text-slate-800 mb-1">{radarData.student.name} ({radarData.student.grade})</h3><RadarChart axes={radarData.axes} /><div className="mt-3 w-full max-w-lg space-y-1">{radarData.axes.map(a=><div key={a.subject_id} className="flex items-center gap-2 text-xs"><span className="w-12 text-slate-600 font-medium">{a.subject}</span><span className="text-orange-600">课前{a.entry_avg_rate}%</span><span className="text-green-600">课后{a.quiz_avg_rate}%</span><span className={`font-medium w-14 text-right ${a.quiz_avg_rate-a.entry_avg_rate>=0?"text-green-600":"text-red-500"}`}>{(a.quiz_avg_rate-a.entry_avg_rate>=0?"+":"")+(a.quiz_avg_rate-a.entry_avg_rate).toFixed(1)}pp</span><span className="text-slate-400 ml-auto">出勤{a.attendance_rate}% · {a.record_count}条</span></div>)}</div></div>}
  </div>;
}

function AIPanel({ students, setError, showSettings, setShowSettings }: {
  students: Student[]; setError: (e:string)=>void; showSettings: boolean; setShowSettings: (v:boolean)=>void;
}) {
  const [studentId, setStudentId] = useState(students[0]?.id||0);
  const [report, setReport] = useState<AiReport|null>(null);
  const [loading, setLoading] = useState(false);
  const [settings, setSettings] = useState<SettingsData|null>(null);
  useEffect(()=>{api.settings.get().then(setSettings).catch(()=>{})},[showSettings]);
  useEffect(()=>{ if(studentId){ api.analysis.latestAiReport(studentId).then(setReport).catch(()=>setReport(null)); } },[studentId]);
  const generate = async() => { setLoading(true); try { setReport(await api.analysis.aiReport(studentId)); } catch(e:any){setError(e.message)} finally{setLoading(false)} };
  const exportPdf = async() => { try { const name = students.find(s=>s.id===studentId)?.name; await api.analysis.aiReportPdf(studentId, name); } catch(e:any){setError(e.message)} };
  return <div className="space-y-4">
    {settings && !settings.deepseek_api_key_set && <div className="bg-amber-50/80 backdrop-blur-sm border border-amber-200/50 rounded-lg p-3 flex items-center justify-between text-sm"><span className="text-amber-700">尚未配置 DeepSeek API Key</span><button onClick={()=>setShowSettings(true)} className="text-indigo-500 hover:text-indigo-700 text-xs underline">立即设置</button></div>}
    <div className="bg-white rounded-lg border p-4"><div className="flex items-center gap-3 mb-4 flex-wrap"><div className="min-w-[200px]"><StudentPicker students={students} value={studentId} onChange={setStudentId} /></div><button onClick={generate} disabled={loading} className="flex items-center gap-1.5 bg-gradient-to-r from-indigo-500 to-violet-500 text-white px-3 py-2 rounded-lg text-sm hover:shadow-md hover:shadow-indigo-500/25 active:scale-[0.97] disabled:opacity-50 transition-all"><Zap className="w-4 h-4" /> {loading?"生成中...":"生成新报告"}</button><button onClick={exportPdf} disabled={loading||!report} className="flex items-center gap-1.5 bg-white border border-slate-200 text-slate-600 px-3 py-2 rounded-lg text-sm hover:bg-slate-50 active:scale-[0.97] disabled:opacity-50 transition-all"><Download className="w-4 h-4" /> 导出 PDF</button></div>
    {loading && <div className="text-sm text-slate-400 py-4 text-center">正在调用 DeepSeek 生成报告...</div>}
    {report && !loading && <div className="bg-slate-50 rounded-lg p-4 border max-h-[600px] overflow-auto"><ReportContent text={report.report} /><div className="mt-3 pt-2 border-t border-slate-200 text-[10px] text-slate-400">模型: {report.model} · 生成时间: {report.generated_at}</div></div>}
    {!report && !loading && <div className="text-sm text-slate-400 py-6 text-center">暂无报告，选择学生后点击"生成新报告"</div>}</div>
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
      <div className="bg-white/90 backdrop-blur-xl rounded-xl shadow-xl w-[420px] max-h-[85vh] overflow-auto animate-modal-in border border-white/30" onClick={e=>e.stopPropagation()}>
        <div className="flex justify-between px-5 py-4 border-b"><h3 className="font-semibold text-slate-800">DeepSeek API 设置</h3><button onClick={onClose} className="hover:rotate-90 transition-transform duration-200"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div>
        <div className="p-5 space-y-4">
          <div><label className="block text-xs font-medium text-slate-600 mb-1">API Key {settings?.deepseek_api_key_set?<span className="text-green-500 text-[10px]">(已设置: {settings.deepseek_api_key_masked})</span>:""}</label><input value={apiKey} onChange={e=>setApiKey(e.target.value)} type="password" className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400/50 bg-white/60" placeholder={settings?.deepseek_api_key_set?"留空则保持不变":"输入 DeepSeek API Key"} /></div>
          <div><label className="block text-xs font-medium text-slate-600 mb-1">模型</label><input value={model} onChange={e=>setModel(e.target.value)} className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400/50 bg-white/60" /></div>
          <div><label className="block text-xs font-medium text-slate-600 mb-1">API 地址</label><input value={baseUrl} onChange={e=>setBaseUrl(e.target.value)} className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400/50 bg-white/60" /></div>
          {testMsg && <div className={`text-xs px-3 py-2 rounded-lg ${testMsg.includes("成功")?"bg-green-50 text-green-700":"bg-red-50 text-red-600"}`}>{testMsg}</div>}
          <div className="flex gap-2"><button onClick={handleTest} disabled={testing} className="flex-1 bg-white border border-slate-200 text-slate-600 py-2 rounded-lg text-sm hover:bg-slate-50 active:scale-[0.97] disabled:opacity-50 transition-all">{testing?"测试中...":"测试连接"}</button><button onClick={handleSave} disabled={saving} className="flex-1 bg-gradient-to-r from-indigo-500 to-violet-500 text-white py-2 rounded-lg text-sm font-medium hover:shadow-md hover:shadow-indigo-500/25 active:scale-[0.97] disabled:opacity-50 transition-all">{saving?"保存中...":"保存"}</button></div>
        </div>
      </div>
    </Modal>
  );
}

// === Simple markdown renderer ===
function ReportContent({ text }: { text: string }) {
  const lines = text.split("\n");
  return <>{lines.map((line, i) => {
    const t = line.trim();
    if (!t) return <div key={i} className="h-2" />;
    if (/^#{1,3}\s/.test(t)) { const lv = (t.match(/^(#{1,3})/)![1]).length; const fs = lv===1?"text-base font-bold":lv===2?"text-sm font-semibold":"text-xs font-semibold"; return <div key={i} className={`${fs} text-slate-800 mt-3 mb-1`}>{t.replace(/^#+\s*/, "")}</div>; }
    if (/^[-*]\s/.test(t)) return <div key={i} className="text-sm text-slate-600 ml-4">• {t.replace(/^[-*]\s+/, "").replace(/\*\*(.+?)\*\*/g, (_,b)=>b)}</div>;
    return <div key={i} className="text-sm text-slate-600 leading-relaxed">{t.replace(/\*\*(.+?)\*\*/g, (_,b)=>b)}</div>;
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
    <div className="p-6">
      <div className="flex justify-between mb-4"><h2 className="text-base font-semibold text-gray-800">成绩管理</h2>
        <button onClick={() => { setEditing(null); setShowForm(true); }} className="flex items-center gap-1.5 bg-gradient-to-r from-indigo-500 to-violet-500 text-white px-3 py-1.5 rounded-lg text-sm hover:shadow-md hover:shadow-indigo-500/25 active:scale-[0.97] transition-all"><FileText className="w-4 h-4" /> 添加成绩</button>
      </div>
      <div className="flex gap-3 mb-3 flex-wrap">
        <div className="min-w-[150px]"><StudentPicker students={[{id:0,name:"全部学生",grade:"",grade_level:""} as any,...students]} value={filterStudent} onChange={setFilterStudent} placeholder="搜索学生..." /></div>
        <select value={filterSubject} onChange={e=>setFilterSubject(+e.target.value)} className="border rounded-md px-2 py-1 text-xs bg-white/70 focus:outline-none focus:ring-2 focus:ring-indigo-400/50 min-w-[100px]"><option value={0}>全部科目</option>{subjects.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select>
        <select value={filterType} onChange={e=>setFilterType(e.target.value)} className="border rounded-md px-2 py-1 text-xs bg-white/70 focus:outline-none focus:ring-2 focus:ring-indigo-400/50 min-w-[100px]"><option value="">全部类型</option><option value="school_exam">学校考试</option><option value="quiz">小测验</option></select>
      </div>
      <div className="bg-white rounded-lg border overflow-hidden">
        <div className="grid grid-cols-[1fr_70px_80px_80px_70px_100px_70px_70px] gap-2 px-4 py-2 bg-slate-50/80 border-b text-xs font-medium text-slate-400"><div>学生</div><div>科目</div><div>类型</div><div>考试名称</div><div>得分</div><div>日期</div><div>得分率</div><div></div></div>
        {loading && <div className="text-xs text-slate-400 py-8 text-center">加载中...</div>}
        {!loading && scores.map(r => (
          <div key={r.id} className="grid grid-cols-[1fr_70px_80px_80px_70px_100px_70px_70px] gap-2 px-4 py-2 border-b text-xs items-center hover:bg-indigo-50/40 transition-colors">
            <div className="font-medium text-slate-800 truncate">{r.student?.name||"—"}</div><div className="text-slate-500">{r.subject?.name||"—"}</div><div className={`px-1 py-0.5 rounded text-[10px] w-fit ${r.exam_type==="school_exam"?"bg-blue-100 text-blue-700":"bg-purple-100 text-purple-700"}`}>{exTypes[r.exam_type]||r.exam_type}</div><div className="truncate">{r.exam_name}</div><div className="text-slate-800 font-medium">{r.score}/{r.max_score}</div><div className="text-slate-400">{r.exam_date}</div><div className={`font-medium ${r.rate>=80?"text-green-600":r.rate>=60?"text-amber-600":"text-red-500"}`}>{r.rate}%</div>
            <div className="flex gap-0.5 justify-end"><button onClick={()=>{setEditing(r);setShowForm(true)}} className="p-0.5 hover:bg-slate-100 rounded"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button><button onClick={async()=>{try{await api.scores.delete(r.id);load()}catch(e:any){setError(e.message)}}} className="p-0.5 hover:bg-red-50 rounded"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></button></div>
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
      <div className="bg-white/90 backdrop-blur-xl rounded-xl shadow-xl w-[420px] max-h-[85vh] overflow-auto animate-modal-in border border-white/30" onClick={e=>e.stopPropagation()}>
        <div className="flex justify-between px-5 py-4 border-b"><h3 className="font-semibold text-slate-800">{record?"编辑成绩":"添加成绩"}</h3><button onClick={onClose} className="hover:rotate-90 transition-transform duration-200"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div>
        <form onSubmit={handle} className="p-5 space-y-3">
          <div><label className="block text-xs font-medium text-slate-600 mb-1">学生</label><StudentPicker students={students} value={studentId} onChange={setStudentId} /></div>
<div className="grid grid-cols-2 gap-3"><div><label className="block text-xs font-medium text-slate-600 mb-1">科目</label><select value={subjectId} onChange={e=>setSubjectId(+e.target.value)} className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400/50 bg-white/60">{subjects.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></div><div><label className="block text-xs font-medium text-slate-600 mb-1">类型</label><div className="flex gap-1 flex-wrap"><button type="button" onClick={()=>{setExamType("school_exam");setCourseId(0)}} className={`px-3 py-1.5 rounded-md text-xs ${examType==="school_exam"?"bg-gradient-to-r from-indigo-500 to-violet-500 text-white":"bg-white/60 border border-slate-200 text-slate-600"}`}>学校考试</button><button type="button" onClick={()=>setExamType("quiz")} className={`px-3 py-1.5 rounded-md text-xs ${examType==="quiz"?"bg-gradient-to-r from-indigo-500 to-violet-500 text-white":"bg-white/60 border border-slate-200 text-slate-600"}`}>补习班测验</button><button type="button" onClick={()=>setExamType("entry_test")} className={`px-3 py-1.5 rounded-md text-xs ${examType==="entry_test"?"bg-gradient-to-r from-orange-500 to-amber-500 text-white":"bg-white/60 border border-slate-200 text-slate-600"}`}>入班诊断</button></div></div></div>
{(examType==="quiz"||examType==="entry_test") && <div><label className="block text-xs font-medium text-slate-600 mb-1">关联课程</label><select value={courseId} onChange={e=>setCourseId(+e.target.value)} className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400/50 bg-white/60"><option value={0}>—不关联—</option>{courses.filter(c=>c.subject_id===subjectId).map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></div>}
          <div><label className="block text-xs font-medium text-slate-600 mb-1">考试/测验名</label><input value={examName} onChange={e=>setExamName(e.target.value)} required className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400/50 bg-white/60" placeholder="如：期中考试、随堂小测" /></div>
          <div className="grid grid-cols-2 gap-3"><div><label className="block text-xs font-medium text-slate-600 mb-1">得分</label><input type="number" value={score} onChange={e=>setScore(+e.target.value)} min={0} step={0.5} required className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400/50 bg-white/60" /></div><div><label className="block text-xs font-medium text-slate-600 mb-1">满分</label><input type="number" value={maxScore} onChange={e=>setMaxScore(+e.target.value)} min={1} required className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400/50 bg-white/60" /></div></div>
          <div><label className="block text-xs font-medium text-slate-600 mb-1">日期</label><input type="date" value={examDate} onChange={e=>setExamDate(e.target.value)} required className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400/50 bg-white/60" /></div>
          <div><label className="block text-xs font-medium text-slate-600 mb-1">备注</label><input value={notes} onChange={e=>setNotes(e.target.value)} className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400/50 bg-white/60" /></div>
          <button type="submit" disabled={saving||studentId===0} className="w-full bg-gradient-to-r from-indigo-500 to-violet-500 text-white py-2 rounded-lg text-sm font-medium hover:shadow-md hover:shadow-indigo-500/25 active:scale-[0.97] disabled:opacity-50 transition-all flex items-center justify-center gap-1.5"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg> {saving?"保存中...":"保存"}</button>
        </form>
      </div>
    </Modal>
  );
}
