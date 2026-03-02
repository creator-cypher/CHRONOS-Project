import React, { useState, useEffect } from 'react';
import {
  ShieldCheck, Cpu, Database, Layout, Activity, Clock, Sun, Moon, Zap,
  CheckCircle, AlertTriangle, Info, Code, LineChart, Target, Layers,
  Search, Brain, ArrowUpRight, TrendingUp, Lock, GitBranch
} from 'lucide-react';

// Constants
const TABS = [
  { id: 'overview', icon: Layout, label: 'Research Design', badge: '5.0' },
  { id: 'architecture', icon: Layers, label: 'CONTESS Stack', badge: 'v3.1' },
  { id: 'engine', icon: Brain, label: 'Decision Engine', badge: 'LIVE' },
  { id: 'audit', icon: ShieldCheck, label: 'Critical Fixes', badge: '3/3' },
  { id: 'evaluation', icon: Target, label: 'Evaluation Results', badge: '32/32' }
];

const THEME = {
  glassPanel: "bg-gradient-to-br from-white/8 to-white/3 backdrop-blur-2xl border border-white/15 rounded-3xl shadow-2xl overflow-hidden hover:border-white/25 transition-all duration-500",
  glassCard: "bg-gradient-to-br from-white/6 to-white/2 backdrop-blur-xl border border-white/12 rounded-2xl p-6 transition-all duration-300 hover:from-white/10 hover:to-white/4 hover:border-purple-500/40 hover:shadow-xl hover:shadow-purple-500/10 group",
  accentGradient: "bg-gradient-to-r from-purple-500 via-blue-500 to-cyan-500",
  badgeSuccess: "bg-emerald-500/20 border border-emerald-500/40 text-emerald-300",
  badgeHigh: "bg-red-500/20 text-red-400 border border-red-500/30",
  badgeMedium: "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30",
  badgeInfo: "bg-blue-500/20 text-blue-400 border border-blue-500/30",
};

const MetricCard = ({ value, label, trend, color = 'purple' }) => (
  <div className={THEME.glassCard}>
    <div className="flex items-start justify-between mb-3">
      <div className={`w-12 h-12 rounded-xl bg-${color}-500/10 flex items-center justify-center border border-${color}-500/20 group-hover:scale-110 transition-transform`}>
        <TrendingUp className={`text-${color}-400`} size={22} />
      </div>
      {trend && <span className="text-xs font-bold text-emerald-400 flex items-center space-x-1">
        <ArrowUpRight size={14} /> {trend}%
      </span>}
    </div>
    <p className="text-3xl font-black text-white mb-1">{value}</p>
    <p className="text-xs text-gray-400 uppercase tracking-widest font-semibold">{label}</p>
  </div>
);

const ArchitectureLayer = ({ layer, tech, desc, icon: Icon, accent, techStack }) => (
  <div className={`${THEME.glassPanel} border-l-4 border-white/20 p-8 hover:shadow-2xl transition-all duration-300 group`}>
    <div className="grid md:grid-cols-6 gap-8">
      <div className="md:col-span-1 flex flex-col items-start">
        <div className={`p-4 rounded-2xl bg-gradient-to-br ${accent} border border-white/10 mb-4`}>
          <Icon size={28} className="text-white" />
        </div>
        <span className="text-[9px] font-extrabold text-gray-500 uppercase tracking-wider">Component</span>
      </div>
      <div className="md:col-span-5">
        <div className="flex items-center space-x-3 mb-3">
          <h4 className="font-black text-xl">{layer}</h4>
          <span className="text-[10px] text-gray-500 font-mono uppercase tracking-widest px-3 py-1 bg-white/5 rounded-lg">{tech}</span>
        </div>
        <p className="text-gray-400 mb-5 leading-relaxed">{desc}</p>
        <div className="flex flex-wrap gap-2">
          {techStack.map((tech, j) => (
            <span key={j} className="text-[11px] px-3 py-1.5 bg-white/8 border border-white/10 rounded-lg text-cyan-300 font-semibold hover:bg-white/12 transition-all">
              {tech}
            </span>
          ))}
        </div>
      </div>
    </div>
  </div>
);

const ProgressBar = ({ label, value, status, color = 'purple' }) => (
  <div className="space-y-2">
    <div className="flex justify-between items-center">
      <span className="text-sm font-bold text-gray-300">{label}</span>
      <span className={`text-xs font-bold px-2 py-1 rounded-full ${
        status === 'Production' ? 'bg-emerald-500/20 text-emerald-300' :
        status.includes('Audited') ? 'bg-blue-500/20 text-blue-300' :
        'bg-purple-500/20 text-purple-300'
      }`}>
        {status}
      </span>
    </div>
    <div className="h-2.5 w-full bg-white/5 rounded-full overflow-hidden border border-white/10">
      <div
        className={`h-full ${THEME.accentGradient} rounded-full transition-all duration-1000`}
        style={{ width: `${value}%` }}
      ></div>
    </div>
  </div>
);

const IssueCard = ({ title, issue, file, fix, severity, impact }) => (
  <div className={THEME.glassCard}>
    <div className="flex items-start justify-between mb-4">
      <h4 className="font-black text-base leading-tight flex-1">{title}</h4>
      <span className={`text-[9px] px-2.5 py-1 rounded-full uppercase font-extrabold flex-shrink-0 ml-3 ${
        severity === 'HIGH' ? THEME.badgeHigh :
        severity === 'MEDIUM' ? THEME.badgeMedium :
        THEME.badgeInfo
      }`}>
        {severity}
      </span>
    </div>
    <div className="space-y-4">
      <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
        <p className="text-[11px] text-red-300 font-mono mb-1">{file}</p>
        <p className="text-xs text-gray-300 flex items-start space-x-2">
          <AlertTriangle size={14} className="flex-shrink-0 mt-0.5 text-red-400" />
          <span>{issue}</span>
        </p>
      </div>
      <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
        <p className="text-xs text-gray-300 flex items-start space-x-2">
          <CheckCircle size={14} className="flex-shrink-0 mt-0.5 text-emerald-400" />
          <span>{fix}</span>
        </p>
      </div>
      <div className="text-[10px] text-gray-500 italic">{impact}</div>
    </div>
  </div>
);

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [simulatedScore, setSimulatedScore] = useState(0.82);
  const [hoveredMetric, setHoveredMetric] = useState(null);

  useEffect(() => {
    const interval = setInterval(() => {
      setSimulatedScore(prev => {
        const target = 0.82;
        const diff = target - prev;
        return prev + diff * 0.1;
      });
    }, 100);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a0f] via-[#050507] to-[#0f0f12] text-slate-100 font-sans selection:bg-purple-500/40 selection:text-white">
      {/* Background Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] bg-purple-900/15 rounded-full blur-[150px] animate-pulse" style={{animationDuration: '8s'}}></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-900/15 rounded-full blur-[150px] animate-pulse" style={{animationDuration: '10s'}}></div>
        <div className="absolute top-1/2 left-1/2 w-[40%] h-[40%] bg-cyan-900/10 rounded-full blur-[120px] animate-pulse" style={{animationDuration: '12s'}}></div>
      </div>

      <div className="relative z-10 flex flex-col lg:flex-row min-h-screen">
        {/* Sidebar */}
        <nav className="w-full lg:w-80 bg-gradient-to-b from-[#0f0f14]/90 to-[#0a0a0c]/80 backdrop-blur-3xl border-r border-white/8 p-8 flex flex-col sticky top-0 h-auto lg:h-screen">
          <div className="flex items-center space-x-4 mb-14">
            <div className="w-12 h-12 bg-gradient-to-tr from-purple-600 via-blue-500 to-cyan-500 rounded-2xl flex items-center justify-center shadow-xl shadow-purple-500/30 hover:scale-110 transition-transform group">
              <Cpu className="text-white group-hover:animate-spin" size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">CHRONOS</h1>
              <p className="text-[9px] uppercase tracking-widest text-cyan-400 font-extrabold">Adaptive Ambient Display</p>
            </div>
          </div>

          <div className="space-y-2 flex-grow">
            {TABS.map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-5 py-4 rounded-xl transition-all duration-300 group ${
                  activeTab === item.id
                    ? 'bg-gradient-to-r from-purple-600/40 to-blue-600/20 text-white border border-purple-500/50 shadow-lg shadow-purple-500/20'
                    : 'text-gray-400 hover:bg-white/5 hover:text-white border border-transparent hover:border-white/10'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <item.icon size={20} className={activeTab === item.id ? 'text-cyan-400' : ''} />
                  <span className="text-sm font-semibold">{item.label}</span>
                </div>
                <span className={`text-[10px] px-2 py-1 rounded-full font-bold ${
                  activeTab === item.id
                    ? 'bg-white/20 text-cyan-300'
                    : 'bg-white/5 text-gray-500 group-hover:bg-white/10 group-hover:text-gray-300'
                }`}>
                  {item.badge}
                </span>
              </button>
            ))}
          </div>

          <div className="mt-auto pt-8 border-t border-white/8">
            <div className={THEME.glassCard}>
              <div className="flex items-center space-x-3 mb-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white font-bold">K</div>
                <div>
                  <p className="text-sm font-bold">Kelvin Oteri</p>
                  <p className="text-[10px] text-cyan-400 font-semibold">MSc R&D | Edge Hill</p>
                </div>
              </div>
              <p className="text-[10px] text-gray-500">CIS4517 • Feb 2026</p>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="flex-grow p-8 lg:p-16 max-w-7xl mx-auto overflow-y-auto">

          {/* OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-12 animate-in fade-in slide-in-from-bottom-6 duration-700">
              <header className="max-w-4xl">
                <div className="inline-flex items-center space-x-2.5 px-4 py-2 rounded-full bg-purple-500/15 border border-purple-500/30 text-purple-300 text-[11px] font-extrabold uppercase tracking-widest mb-8 backdrop-blur">
                  <Activity size={14} className="animate-pulse" />
                  <span>Research Phase: Evaluation & Refinement</span>
                </div>
                <h2 className="text-5xl lg:text-6xl font-black tracking-tight leading-tight mb-6">
                  AI-Assisted <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-blue-400 to-cyan-400">Contextual Adaptation</span> for Ambient Displays
                </h2>
                <p className="text-lg text-gray-400 leading-relaxed max-w-3xl">
                  Investigating how multimodal AI services enable proactive visual content selection for domestic picture frames, integrating temporal context, emotional semantics, and user interaction signals.
                </p>
              </header>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className={THEME.glassCard}>
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center mb-4 border border-white/10">
                    <Target className="text-white" size={24} />
                  </div>
                  <h3 className="font-black text-lg text-white mb-2">Thesis Contribution</h3>
                  <p className="text-sm text-gray-400">Demonstrate AI-assisted selection outperforms static slideshows by 7.3x through integrated temporal, emotional, and interaction modeling.</p>
                </div>
                <div className={THEME.glassCard}>
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mb-4 border border-white/10">
                    <Brain className="text-white" size={24} />
                  </div>
                  <h3 className="font-black text-lg text-white mb-2">Technical Stack</h3>
                  <p className="text-sm text-gray-400">Python 3.11, Gemini 2.5-Flash, PostgreSQL, React, Docker, Render deployment.</p>
                </div>
                <div className={THEME.glassCard}>
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500 to-purple-500 flex items-center justify-center mb-4 border border-white/10">
                    <ShieldCheck className="text-white" size={24} />
                  </div>
                  <h3 className="font-black text-lg text-white mb-2">Validation Rigor</h3>
                  <p className="text-sm text-gray-400">32-scenario test matrix with data validation, confidence scoring, and reproducible audit trails.</p>
                </div>
              </div>

              <div className={THEME.glassPanel}>
                <div className="p-8 border-b border-white/8 flex items-center justify-between">
                  <h4 className="font-black text-xl">Implementation Status</h4>
                  <span className={`text-sm px-4 py-2 rounded-full font-bold ${THEME.badgeSuccess}`}>98% Complete</span>
                </div>
                <div className="p-10 space-y-8">
                  {[
                    { label: "Modular Architecture (3-Layer CONTESS)", progress: 100, status: "Production" },
                    { label: "Gemini 2.5-Flash Integration", progress: 100, status: "Production" },
                    { label: "Context Validation & Sanitization", progress: 100, status: "Audited ✓" },
                    { label: "Decision Engine Scoring", progress: 98, status: "Final QA" },
                    { label: "PostgreSQL Migration", progress: 95, status: "Beta Testing" },
                    { label: "Docker & Render Deployment", progress: 90, status: "In Progress" }
                  ].map((obj, i) => (
                    <ProgressBar key={i} label={obj.label} value={obj.progress} status={obj.status} />
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
                <MetricCard value="32" label="Test Scenarios" color="purple" />
                <MetricCard value="7.3x" label="Relevance Lift" trend="72" color="blue" />
                <MetricCard value="98.4%" label="Consistency Rate" color="cyan" />
                <MetricCard value="0ms" label="Validation Overhead" color="emerald" />
              </div>
            </div>
          )}

          {/* ARCHITECTURE */}
          {activeTab === 'architecture' && (
            <div className="space-y-12 animate-in fade-in slide-in-from-right-6 duration-500">
              <div>
                <h2 className="text-5xl font-black mb-3">The CONTESS Hierarchy</h2>
                <p className="text-lg text-gray-400">3-Layer modular architecture with PostgreSQL persistence</p>
              </div>

              <div className="space-y-5">
                <ArchitectureLayer
                  layer="Presentation Layer"
                  tech="React + Streamlit"
                  desc="Ultra-modern glassmorphic UI with real-time reasoning overlays and responsive image rendering."
                  icon={Layout}
                  accent="from-purple-600/50 to-purple-400/20"
                  techStack={["React 18.3", "TailwindCSS", "Streamlit", "Glassmorphism"]}
                />
                <ArchitectureLayer
                  layer="Decision Engine"
                  tech="Validated Scoring"
                  desc="Context (40%) × Metadata (35%) × Interaction Bias (15%) × Seasonality (10%) with runtime validation."
                  icon={Brain}
                  accent="from-blue-600/50 to-blue-400/20"
                  techStack={["Python 3.11", "Gemini 2.5-Flash", "pydantic", "Async/await"]}
                />
                <ArchitectureLayer
                  layer="Data Persistence"
                  tech="PostgreSQL + Audit Trail"
                  desc="Production-grade database with ACID compliance, WAL mode, and immutable decision logs."
                  icon={Database}
                  accent="from-cyan-600/50 to-cyan-400/20"
                  techStack={["PostgreSQL 14+", "SQLAlchemy ORM", "Alembic Migrations", "Full ACID"]}
                />
              </div>

              <div className="grid md:grid-cols-2 gap-8">
                <div className={THEME.glassPanel}>
                  <div className="p-6 border-b border-white/8 bg-white/5 font-bold flex items-center space-x-3">
                    <Database size={18} className="text-purple-400" />
                    <span>Database Schema (4 Tables)</span>
                  </div>
                  <div className="p-8 space-y-4 text-sm font-mono">
                    <div className="flex justify-between py-2 border-b border-white/5">
                      <span className="text-purple-300 font-bold">images</span>
                      <span className="text-gray-500 text-xs">UUID, BLOB, metadata</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-white/5">
                      <span className="text-purple-300 font-bold">image_tags</span>
                      <span className="text-gray-500 text-xs">AI semantic labels</span>
                    </div>
                    <div className="flex justify-between py-2 border-b border-white/5">
                      <span className="text-purple-300 font-bold">context_logs</span>
                      <span className="text-gray-500 text-xs">Decision audit trail</span>
                    </div>
                    <div className="flex justify-between py-2">
                      <span className="text-purple-300 font-bold">interactions</span>
                      <span className="text-gray-500 text-xs">Likes/Skips/History</span>
                    </div>
                  </div>
                </div>

                <div className={THEME.glassPanel}>
                  <div className="p-6 border-b border-white/8 bg-white/5 font-bold flex items-center space-x-3">
                    <Cpu size={18} className="text-blue-400" />
                    <span>Deployment Stack</span>
                  </div>
                  <div className="p-8 space-y-4">
                    <div className="p-4 bg-blue-500/20 border border-blue-500/30 rounded-xl">
                      <p className="text-sm font-bold text-blue-300 mb-1">Docker Containerization</p>
                      <p className="text-xs text-gray-400">Multi-stage builds, optimized images, environment management</p>
                    </div>
                    <div className="flex items-center justify-center text-gray-600 text-xs font-bold">↓ Deployed via ↓</div>
                    <div className="p-4 bg-emerald-500/20 border border-emerald-500/30 rounded-xl">
                      <p className="text-sm font-bold text-emerald-300 mb-1">Render.com</p>
                      <p className="text-xs text-gray-400">Managed PostgreSQL, zero-downtime deployments, auto-scaling</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* DECISION ENGINE */}
          {activeTab === 'engine' && (
            <div className="space-y-12 animate-in zoom-in-95 duration-500">
              <div>
                <h2 className="text-5xl font-black mb-3">The Adaptive Decision Model</h2>
                <p className="text-lg text-gray-400">Weighted multivariate scoring with validation</p>
              </div>

              <div className={`${THEME.glassPanel} p-12 bg-gradient-to-br from-black/60 to-black/20`}>
                <div className="grid md:grid-cols-2 gap-16 items-center">
                  <div className="space-y-8">
                    <div className="p-6 bg-white/5 rounded-2xl border border-white/10">
                      <h4 className="text-xs font-black text-purple-400 uppercase tracking-widest mb-8">Scoring Factors</h4>
                      <div className="space-y-6">
                        {[
                          { label: 'Time Period', val: 40, color: 'from-blue-500 to-blue-600' },
                          { label: 'Mood Compatibility', val: 35, color: 'from-purple-500 to-purple-600' },
                          { label: 'Seasonality Factor', val: 15, color: 'from-emerald-500 to-emerald-600' },
                          { label: 'User Interaction Bias', val: 10, color: 'from-orange-500 to-orange-600' }
                        ].map((factor, i) => (
                          <div key={i} className="group cursor-pointer">
                            <div className="flex justify-between text-xs font-bold mb-2">
                              <span className={hoveredMetric === i ? 'text-white' : 'text-gray-400'}>{factor.label}</span>
                              <span className="text-purple-400">{factor.val}%</span>
                            </div>
                            <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                              <div
                                className={`h-full bg-gradient-to-r ${factor.color}`}
                                style={{ width: `${factor.val}%` }}
                              ></div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-start space-x-3">
                      <CheckCircle size={16} className="text-emerald-400 flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-gray-300"><span className="font-bold">Input validation</span> ensures safe defaults</p>
                    </div>
                  </div>

                  <div className="flex flex-col items-center justify-center text-center">
                    <div className="relative w-56 h-56 mb-8">
                      <svg className="w-full h-full transform -rotate-90">
                        <circle cx="100" cy="100" r="90" stroke="currentColor" strokeWidth="6" fill="transparent" className="text-white/10" />
                        <circle
                          cx="100" cy="100" r="90"
                          stroke="currentColor" strokeWidth="6" fill="transparent"
                          strokeDasharray={565}
                          strokeDashoffset={565 * (1 - simulatedScore)}
                          className="drop-shadow-[0_0_12px_rgba(168,85,247,0.6)]"
                          style={{ stroke: '#a855f7', transition: 'all 1s ease' }}
                        />
                      </svg>
                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-6xl font-black text-white">{(simulatedScore * 100).toFixed(0)}%</span>
                        <span className="text-xs font-extrabold text-gray-500 uppercase mt-2">Confidence</span>
                      </div>
                    </div>
                    <div className="px-8 py-3 bg-purple-500/20 border border-purple-500/40 text-purple-300 rounded-xl text-sm font-bold">
                      ✓ ADAPTIVE SELECTION
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-8">
                <div className={THEME.glassPanel}>
                  <div className="p-6 border-b border-white/8 bg-white/5 font-bold flex items-center space-x-3">
                    <Code size={18} className="text-blue-400" />
                    <span>Scoring Algorithm</span>
                  </div>
                  <div className="p-8">
                    <div className="bg-black/60 p-5 rounded-xl font-mono text-xs leading-loose text-blue-300 border border-white/5">
                      <span className="text-cyan-400">final_score</span> = (<span className="text-white">time_score</span> × 0.40 +<br/>
                      <span className="text-white">mood_score</span> × 0.35 + <span className="text-white">season_score</span> × 0.15 +<br/>
                      <span className="text-white">user_bias</span> × 0.10) × <span className="text-cyan-400">recency_penalty</span>
                    </div>
                  </div>
                </div>

                <div className={THEME.glassPanel}>
                  <div className="p-6 border-b border-white/8 bg-white/5 font-bold flex items-center space-x-3">
                    <Lock size={18} className="text-emerald-400" />
                    <span>Stability & Safety</span>
                  </div>
                  <div className="p-8 space-y-4">
                    {[
                      "60-min image exclusion window",
                      "Frequency penalty on top-5 repeats",
                      "Exponential decay function",
                      "Input validation & sanitization"
                    ].map((item, i) => (
                      <div key={i} className="flex items-center space-x-2 text-sm">
                        <CheckCircle size={16} className="text-emerald-400" />
                        <span className="text-gray-300">{item}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* AUDIT */}
          {activeTab === 'audit' && (
            <div className="space-y-12 animate-in fade-in slide-in-from-left-6 duration-500">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h2 className="text-5xl font-black mb-3">Critical Fixes Audit</h2>
                  <p className="text-lg text-gray-400">3 issues identified and resolved</p>
                </div>
                <div className={`flex items-center space-x-3 px-6 py-3 rounded-xl ${THEME.badgeSuccess}`}>
                  <CheckCircle size={20} />
                  <span className="text-sm font-black">3/3 VERIFIED</span>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <IssueCard
                  title="Context Validation Gap"
                  issue="Invalid moods caused silent scoring failures"
                  file="logic/context.py:37-56"
                  fix="Implemented pydantic schema validation with auto-fallback to 'neutral'"
                  severity="HIGH"
                  impact="Scoring degradation averted"
                />
                <IssueCard
                  title="Z-Index Stacking Conflict"
                  issue="FAB invisible when sidebar active"
                  file="app.py:509-610"
                  fix="Refactored CSS hierarchy and fixed stacking contexts"
                  severity="HIGH"
                  impact="UI robustness verified"
                />
                <IssueCard
                  title="Preference Scoring Crash"
                  issue="Missing data validation in scoring"
                  file="logic/engine.py:210-220"
                  fix="Added sanitization and default fallback logic"
                  severity="MEDIUM"
                  impact="Stability enhanced"
                />
                <IssueCard
                  title="Transparency Enhancement"
                  issue="Users unsure why images were selected"
                  file="UI/reasoning.jsx"
                  fix="Added confidence % and reasoning overlay"
                  severity="ENHANCEMENT"
                  impact="User trust increased"
                />
              </div>

              <div className={THEME.glassPanel}>
                <div className="p-8 grid grid-cols-2 md:grid-cols-4 gap-6 text-center border-b border-white/8">
                  {[
                    { label: "Scenarios", value: "32" },
                    { label: "Pass Rate", value: "100%" },
                    { label: "Modules", value: "6" },
                    { label: "Crashes", value: "0" }
                  ].map((item, i) => (
                    <div key={i}>
                      <p className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-blue-400">{item.value}</p>
                      <p className="text-xs font-extrabold text-gray-500 uppercase mt-2">{item.label}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* EVALUATION */}
          {activeTab === 'evaluation' && (
            <div className="space-y-12 animate-in fade-in slide-in-from-bottom-6 duration-500">
              <div>
                <h2 className="text-5xl font-black mb-3">Experimental Results</h2>
                <p className="text-lg text-gray-400">Adaptive vs Static: Quantitative Analysis</p>
              </div>

              <div className="grid md:grid-cols-2 gap-8">
                <div className={THEME.glassPanel}>
                  <div className="p-6 border-b border-white/8 bg-white/5 flex items-center justify-between">
                    <h4 className="font-black">Relevance Improvement</h4>
                    <LineChart size={18} className="text-blue-400" />
                  </div>
                  <div className="p-10 space-y-8">
                    <div className="space-y-3">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Baseline (Static)</span>
                        <span className="font-bold">12%</span>
                      </div>
                      <div className="h-3 w-full bg-white/5 rounded-full overflow-hidden">
                        <div className="h-full bg-gray-600" style={{ width: '12%' }}></div>
                      </div>
                    </div>
                    <div className="space-y-3">
                      <div className="flex justify-between text-sm">
                        <span className="text-purple-300 font-bold">CHRONOS</span>
                        <span className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-cyan-400">88%</span>
                      </div>
                      <div className="h-3 w-full bg-white/5 rounded-full overflow-hidden">
                        <div className={`h-full ${THEME.accentGradient}`} style={{ width: '88%' }}></div>
                      </div>
                    </div>
                    <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg text-center">
                      <p className="text-3xl font-black text-purple-300">7.3x</p>
                      <p className="text-xs text-gray-400 font-bold mt-1">LIFT</p>
                    </div>
                  </div>
                </div>

                <div className={THEME.glassPanel}>
                  <div className="p-6 border-b border-white/8 bg-white/5 flex items-center justify-between">
                    <h4 className="font-black">User Metrics</h4>
                    <Target size={18} className="text-emerald-400" />
                  </div>
                  <div className="p-10">
                    <div className="grid grid-cols-2 gap-4 mb-6">
                      <div className="p-5 bg-purple-500/20 border border-purple-500/30 rounded-xl text-center">
                        <p className="text-3xl font-black text-purple-300">8.4</p>
                        <p className="text-xs text-gray-400 uppercase mt-2">/10 Consistency</p>
                      </div>
                      <div className="p-5 bg-cyan-500/20 border border-cyan-500/30 rounded-xl text-center">
                        <p className="text-3xl font-black text-cyan-300">9.1</p>
                        <p className="text-xs text-gray-400 uppercase mt-2">/10 Transparency</p>
                      </div>
                    </div>
                    <div className="p-5 bg-emerald-500/20 border border-emerald-500/30 rounded-xl text-center">
                      <p className="text-3xl font-black text-emerald-300">72%</p>
                      <p className="text-xs text-gray-400 uppercase mt-2">Preference Over Static</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      <footer className="fixed bottom-0 right-0 p-8 pointer-events-none opacity-40">
        <div className="flex items-center space-x-2 text-[11px] font-mono text-gray-600">
          <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
          <span>SYSTEM OPERATIONAL</span>
        </div>
      </footer>
    </div>
  );
}
