import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import {
  Activity, Bot, Clock, MessageSquareText, Send, ShieldAlert,
  Sparkles, TrendingDown, TrendingUp,
} from "lucide-react";
import { api } from "./api";
import { ReportContent } from "./Analytics";
import type { CourseHealthItem, RiskStudentItem } from "./types";
import { DAY_NAMES, TIME_SLOTS } from "./types";

type ChatMessage = { role: "user" | "assistant"; content: string };

const QUICK_PROMPTS = [
  "给出一份机构运营健康报告",
  "分析当前最需要干预的学生",
  "哪些课程的排课或资源需要优化？",
  "结合最近趋势给出下一周教学建议",
];

function ChatPanel({ setError }: { setError: (e: string) => void }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const send = async (raw = input) => {
    const text = raw.trim();
    if (!text || loading) return;
    const history = messages
      .filter((m) => m.role !== "assistant" || !m.content.startsWith("生成失败"))
      .slice(-8)
      .map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.analysis.aiInsight({ insight_type: "qa", question: text, history });
      setMessages((prev) => [...prev, { role: "assistant", content: res.answer }]);
    } catch (e: any) {
      const msg = e.message || "AI 问答失败";
      setError(msg);
      setMessages((prev) => [...prev, { role: "assistant", content: `生成失败：${msg}` }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    send();
  };

  return (
    <section className="dash-module ai-chat-module">
      <div className="dash-module-head">
        <div>
          <h3>AI 数据分析问答</h3>
          <p>基于实时机构数据回答问题，不做凭空推测</p>
        </div>
        <Bot className="dash-module-icon" />
      </div>
      <div className="ai-chat-quick">
        {QUICK_PROMPTS.map((q) => (
          <button key={q} className="chip" onClick={() => send(q)} disabled={loading}>
            {q}
          </button>
        ))}
      </div>
      <div className="ai-chat-window">
        {messages.length === 0 && (
          <div className="ai-chat-empty">
            <MessageSquareText />
            <p>输入问题或点击上方快捷提问，AI 会结合当前数据库给出可执行建议。</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`ai-chat-msg ${m.role}`}>
            <div className="ai-chat-avatar">{m.role === "user" ? "我" : <Bot />}</div>
            <div className="ai-chat-bubble">
              {m.role === "user" ? <p>{m.content}</p> : <ReportContent text={m.content} />}
            </div>
          </div>
        ))}
        {loading && (
          <div className="ai-chat-msg assistant">
            <div className="ai-chat-avatar"><Bot /></div>
            <div className="ai-chat-bubble ai-typing"><span /><span /><span /></div>
          </div>
        )}
      </div>
      <form onSubmit={handleSubmit} className="ai-chat-input">
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="问任何关于课程、学生、出勤、成绩的问题..." className="field" />
        <button type="submit" disabled={loading || !input.trim()} className="primary-btn">
          <Send className="w-4 h-4" /> 发送
        </button>
      </form>
    </section>
  );
}

function HealthPanel({ setError }: { setError: (e: string) => void }) {
  const [health, setHealth] = useState<CourseHealthItem[]>([]);
  const [loading, setLoading] = useState(true);
  const load = async () => {
    setLoading(true);
    try {
      setHealth(await api.analysis.courseHealth());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);
  return (
    <section className="dash-module">
      <div className="dash-module-head">
        <div>
          <h3>课程健康度分析</h3>
          <p>按健康分从低到高排序，优先关注需要干预的课程</p>
        </div>
        <Activity className="dash-module-icon" />
      </div>
      {loading && <div className="report-loading">正在计算课程健康度...</div>}
      {!loading && (
        <div className="table-panel health-table">
          <div className="grid grid-cols-[1.4fr_1fr_1fr_1fr_110px_90px] gap-3 px-4 py-2 table-head border-b text-xs font-medium text-slate-400">
            <div>课程</div><div>出勤率</div><div>得分率</div><div>满员率</div><div>健康分</div><div>状态</div>
          </div>
          {health.length === 0 && <div className="text-xs text-slate-400 py-8 text-center">暂无课程数据</div>}
          {health.map((h) => (
            <div key={h.course_id} className="grid grid-cols-[1.4fr_1fr_1fr_1fr_110px_90px] gap-3 px-4 py-3 border-b last:border-0 text-sm items-center hover:bg-white/8">
              <div className="min-w-0">
                <div className="font-medium text-slate-800 truncate">{h.name}</div>
                <div className="text-[11px] text-slate-400 truncate">{h.subject} · {h.teacher} · {DAY_NAMES[h.day]} {TIME_SLOTS[h.slot - 1]}</div>
              </div>
              <div className="health-cell"><span>{h.attendance_rate}%</span><div className="progress-track"><div className="fill-good" style={{ width: `${h.attendance_rate}%` }} /></div></div>
              <div className="health-cell"><span>{h.score_rate}%</span><div className="progress-track"><div className="fill-mid" style={{ width: `${h.score_rate}%` }} /></div></div>
              <div className="health-cell"><span>{h.utilization}%</span><div className="progress-track"><div className="fill-low" style={{ width: `${h.utilization}%` }} /></div></div>
              <div className="health-score-cell">
                <b className={h.health_score >= 80 ? "text-green-600" : h.health_score >= 65 ? "text-amber-600" : "text-red-500"}>{h.health_score}</b>
              </div>
              <div>
                <span className={`status-chip text-xs px-2 py-0.5 risk-${h.risk_level}`}>
                  {h.risk_level === "high" ? "高危" : h.risk_level === "medium" ? "关注" : "稳定"}
                </span>
              </div>
              {h.signals.length > 0 && (
                <div className="col-span-6 flex gap-1 flex-wrap pb-1 -mt-1">
                  {h.signals.map((s) => <span key={s} className="signal-chip">{s}</span>)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function RiskPanel({ setError }: { setError: (e: string) => void }) {
  const [risk, setRisk] = useState<RiskStudentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const load = async () => {
    setLoading(true);
    try {
      setRisk(await api.analysis.risk());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);
  return (
    <section className="dash-module">
      <div className="dash-module-head">
        <div>
          <h3>学生风险预警</h3>
          <p>结合出勤率、得分率、成绩趋势与近期缺勤计算风险</p>
        </div>
        <ShieldAlert className="dash-module-icon" />
      </div>
      {loading && <div className="report-loading">正在分析学生风险...</div>}
      {!loading && (
        <div className="risk-list risk-list-wide">
          {risk.length === 0 && <div className="chart-empty">暂无学生数据</div>}
          {risk.map((r) => (
            <div key={r.student_id} className="risk-row">
              <div className="risk-ring" style={{ "--risk": `${Math.min(99, r.risk_score) * 3.6}deg` } as CSSProperties}>
                <span>{r.risk_score}</span>
              </div>
              <div className="risk-body">
                <div className="risk-name">
                  <strong>{r.name}</strong>
                  <span className={`risk-badge risk-${r.risk_level}`}>
                    {r.risk_level === "high" ? "高危" : r.risk_level === "medium" ? "关注" : "稳定"}
                  </span>
                  <span className="risk-course"><Clock /> {r.courses}门课</span>
                </div>
                <p>{r.grade_level}{r.grade} · 出勤{r.attendance_rate}% · 成绩{r.score_rate}% · 近30天缺勤{r.recent_absences}次</p>
                <div className="risk-trend-row">
                  {r.trend_delta !== 0 && (
                    <span className={r.trend_delta > 0 ? "trend-up" : "trend-down"}>
                      {r.trend_delta > 0 ? <TrendingUp /> : <TrendingDown />} 成绩趋势 {r.trend_delta > 0 ? "+" : ""}{r.trend_delta}pp
                    </span>
                  )}
                </div>
                {r.signals.length > 0 && (
                  <div className="signal-row">{r.signals.map((s) => <span key={s} className="signal-chip">{s}</span>)}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export function AiLabView({ setError }: { setError: (e: string) => void }) {
  const [tab, setTab] = useState<"chat" | "health" | "risk">("chat");
  const tabs = [
    { id: "chat" as const, label: "AI 问答", icon: MessageSquareText },
    { id: "health" as const, label: "课程健康度", icon: Activity },
    { id: "risk" as const, label: "风险预警", icon: ShieldAlert },
  ];
  return (
    <div className="view-page p-6">
      <div className="dashboard-head">
        <div>
          <h2>AI 教学助手</h2>
          <p>对话式数据分析、课程诊断与风险预警</p>
        </div>
        <span className="status-chip status-ok"><Sparkles className="w-3.5 h-3.5" /> DeepSeek 增强</span>
      </div>
      <div className="flex gap-2 mb-4">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)} className={`chip ${tab === t.id ? "active" : ""}`}>
            <t.icon className="w-3.5 h-3.5" /> {t.label}
          </button>
        ))}
      </div>
      {tab === "chat" && <ChatPanel setError={setError} />}
      {tab === "health" && <HealthPanel setError={setError} />}
      {tab === "risk" && <RiskPanel setError={setError} />}
    </div>
  );
}
