import React, { useState } from "react";
import {
  Activity, CalendarDays, BarChart3, Clapperboard,
  Clock3, FileText, Film, Image, Instagram, LayoutDashboard,
  Menu, Plus, Settings, ShieldCheck, Sparkles, X, Zap
} from "lucide-react";

const initialPosts = [
  { id: 1, type: "REEL", title: "New tax regime: 3 things to know", time: "10:00 AM", status: "Draft", tag: "Taxation" },
  { id: 2, type: "STORY", title: "Today's finance quiz", time: "12:00 PM", status: "Scheduled", tag: "Personal finance" },
  { id: 3, type: "STORY", title: "Accounting concept in 30 seconds", time: "4:00 PM", status: "Scheduled", tag: "Accounting" },
  { id: 4, type: "STORY", title: "Save this money tip", time: "8:00 PM", status: "Scheduled", tag: "Personal finance" }
];

const navItems = [
  ["Overview", LayoutDashboard],
  ["Content calendar", CalendarDays],
  ["Reel studio", Clapperboard],
  ["Story studio", Image],
  ["Publishing", Instagram],
  ["Analytics", BarChart3],
  ["Settings", Settings]
];

export default function App() {
  const [active, setActive] = useState("Overview");
  const [menuOpen, setMenuOpen] = useState(false);
  const [posts, setPosts] = useState(initialPosts);

  const saveReelDraft = (title) => {
    setPosts((items) => [
      { id: Date.now(), type: "REEL", title, time: "Not scheduled", status: "Draft", tag: "Reel Studio" },
      ...items
    ]);
    setActive("Overview");
  };

  const addDraft = () => {
    setPosts((items) => [
      { id: Date.now(), type: "REEL", title: "New content idea — add your topic", time: "Not scheduled", status: "Draft", tag: "Unassigned" },
      ...items
    ]);
    setActive("Reel studio");
  };

  return (
    <div className="app-shell">
      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><Zap size={20} fill="currentColor" /></div>
          <div><strong>ReelPilot</strong><span>AI STUDIO</span></div>
          <button className="icon-btn close-menu" onClick={() => setMenuOpen(false)} aria-label="Close menu"><X size={19}/></button>
        </div>
        <div className="workspace-label">WORKSPACE</div>
        <nav>
          {navItems.map(([label, Icon]) => (
            <button key={label} className={`nav-link ${active === label ? "active" : ""}`} onClick={() => { setActive(label); setMenuOpen(false); }}>
              <Icon size={18}/><span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="connection-dot"><span/> Instagram not connected</div>
          <p>Connect your professional account to enable publishing.</p>
          <button className="connect-btn" onClick={() => { setActive("Settings"); setMenuOpen(false); }}>Set up account</button>
          <div className="version">REELPILOT AI · v0.1.0</div>
        </div>
      </aside>

      {menuOpen && <button className="scrim" onClick={() => setMenuOpen(false)} aria-label="Close navigation"/>}

      <main className="main">
        <header className="topbar">
          <button className="icon-btn mobile-menu" onClick={() => setMenuOpen(true)} aria-label="Open menu"><Menu size={21}/></button>
          <div className="breadcrumb">Workspace <span>/</span> {active}</div>
          <div className="topbar-right"><span className="local-time"><span/> System ready</span><div className="avatar">RP</div></div>
        </header>

        <div className="content">
          <section className="welcome-row">
            <div>
              <div className="eyebrow"><Sparkles size={14}/> YOUR CONTENT COMMAND CENTRE</div>
              <h1>{active === "Overview" ? "Good to see you." : active}</h1>
              <p className="subheading">{active === "Overview" ? "Plan, create and publish finance content from one place." : sectionDescription(active)}</p>
            </div>
            <button className="primary-btn" onClick={addDraft}><Plus size={17}/> Create content</button>
          </section>

          <section className="notice">
            <div className="notice-icon"><ShieldCheck size={19}/></div>
            <div><strong>Setup mode — publishing is not active</strong><p>This dashboard is an initial UI. Connect Meta and configure the content engine before enabling automatic publishing.</p></div>
          </section>

          {active === "Reel studio" ? (
            <ReelStudio onSave={saveReelDraft} />
          ) : (
            <>
          <section className="stats-grid">
            <Stat icon={Film} label="Reels today" value="1" detail="Daily target" />
            <Stat icon={Image} label="Stories today" value="3" detail="Daily target" />
            <Stat icon={Clock3} label="In publishing queue" value={String(posts.filter(p => p.status === "Scheduled").length)} detail="Demo records" />
            <Stat icon={Activity} label="Published" value="0" detail="No account connected" />
          </section>

          <section className="panel content-panel">
            <div className="panel-heading">
              <div><h2>Today's content plan</h2><p>Your daily Reel and Story schedule</p></div>
              <button className="text-btn" onClick={() => setActive("Content calendar")}>View calendar <span>→</span></button>
            </div>
            <div className="post-list">
              {posts.map(post => (
                <div className="post-row" key={post.id}>
                  <div className={`post-icon ${post.type.toLowerCase()}`}>{post.type === "REEL" ? <Film size={18}/> : <Image size={18}/>}</div>
                  <div className="post-info"><div className="post-title">{post.title}</div><div className="post-meta">{post.type} <span>·</span> {post.tag}</div></div>
                  <div className="post-time">{post.time}</div>
                  <span className={`status ${post.status.toLowerCase()}`}>{post.status}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="bottom-grid">
            <div className="panel setup-panel">
              <div className="panel-heading"><div><h2>Getting started</h2><p>Complete these steps to activate automation</p></div><span className="progress-count">0 / 4</span></div>
              <SetupStep number="01" title="Connect Instagram Business" detail="Link your professional account through Meta."/>
              <SetupStep number="02" title="Configure content preferences" detail="Choose topics, voice, language and brand style."/>
              <SetupStep number="03" title="Generate your first Reel" detail="Create a test video and review its quality."/>
              <SetupStep number="04" title="Enable scheduled publishing" detail="Activate only after testing and permissions."/>
            </div>
            <div className="panel engine-panel">
              <div className="engine-icon"><Sparkles size={20}/></div>
              <h2>AI content engine</h2>
              <p>Research topics, write Hinglish scripts, generate voiceovers and render vertical videos.</p>
              <div className="engine-state"><span/> Waiting for configuration</div>
              <button className="secondary-btn" onClick={() => setActive("Settings")}>Configure engine</button>
            </div>
          </section>
          <footer>ReelPilot AI <span>·</span> Built for responsible finance education <span>·</span> Demo data only</footer>
            </>
          )}
        </div>
      </main>
    </div>
  );
}


function ReelStudio({ onSave }) {
  const [topic, setTopic] = useState("");
  const [format, setFormat] = useState("Explainer");
  const [duration, setDuration] = useState("30 seconds");
  const [script, setScript] = useState("");
  const [caption, setCaption] = useState("");
  const [error, setError] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);

  const generateDraft = async () => {
    const cleanTopic = topic.trim();
    if (cleanTopic.length < 4) {
      setError("Please enter a topic with at least 4 characters.");
      return;
    }

    const apiBase = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
    if (!apiBase) {
      setError("AI backend is not connected yet. The backend must be deployed and VITE_API_BASE_URL configured first.");
      return;
    }

    setError("");
    setIsGenerating(true);
    try {
      const response = await fetch(`${apiBase}/api/generate-reel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: cleanTopic, format, duration })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || "Could not generate the script. Please try again.");
      }
      setScript(data.script || "");
      setCaption([data.caption, data.hashtags].filter(Boolean).join("\n\n"));
    } catch (err) {
      setError(err.message || "Could not connect to the AI backend.");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <section className="studio-layout">
      <div className="panel studio-form">
        <div className="panel-heading">
          <div><h2><Clapperboard size={18} /> Reel brief</h2><p>Build a structured script draft for a faceless Reel.</p></div>
          <span className="progress-count">DRAFT MODE</span>
        </div>
        <label className="field-label" htmlFor="reel-topic">What is the Reel about?</label>
        <textarea id="reel-topic" className="studio-input topic-input" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g. New tax regime vs old tax regime" rows={3} />
        <div className="studio-fields">
          <div>
            <label className="field-label" htmlFor="reel-format">Content format</label>
            <select id="reel-format" className="studio-input" value={format} onChange={(e) => setFormat(e.target.value)}>
              <option>Explainer</option><option>Myth vs fact</option><option>3 quick points</option>
            </select>
          </div>
          <div>
            <label className="field-label" htmlFor="reel-duration">Target duration</label>
            <select id="reel-duration" className="studio-input" value={duration} onChange={(e) => setDuration(e.target.value)}>
              <option>30 seconds</option><option>60 seconds</option>
            </select>
          </div>
        </div>
        {error && <p className="studio-error">{error}</p>}
        <button className="primary-btn studio-generate" onClick={generateDraft} disabled={isGenerating}><Sparkles size={17}/> {isGenerating ? "Generating with Gemini..." : "Generate AI script"}</button>
        <p className="studio-disclaimer">AI-generated drafts are not tax- or fact-verified. Verify every legal, tax and financial claim against current official sources before publishing.</p>
      </div>
      <div className="panel studio-output">
        <div className="panel-heading"><div><h2><FileText size={18}/> Script preview</h2><p>Hook · Explanation · Call to action</p></div></div>
        {script ? (
          <>
            <pre className="script-preview">{script}</pre>
            <label className="field-label">Caption and hashtags</label>
            <textarea className="studio-input caption-input" value={caption} onChange={(e) => setCaption(e.target.value)} rows={5} />
            <button className="secondary-btn" onClick={() => onSave(topic.trim())}>Save as Reel draft</button>
          </>
        ) : (
          <div className="studio-empty"><div className="engine-icon"><Film size={20}/></div><strong>Your script will appear here</strong><p>Enter a topic and create a draft to preview its structure.</p></div>
        )}
      </div>
    </section>
  );
}

function Stat({ icon: Icon, label, value, detail }) {
  return <div className="stat-card"><div className="stat-top"><span>{label}</span><Icon size={17}/></div><div className="stat-value">{value}</div><div className="stat-detail">{detail}</div></div>;
}

function SetupStep({ number, title, detail }) {
  return <div className="setup-step"><span className="step-number">{number}</span><div><strong>{title}</strong><p>{detail}</p></div><span className="step-arrow">›</span></div>;
}

function sectionDescription(section) {
  const descriptions = {
    "Content calendar": "Organise your daily content and publishing schedule.",
    "Reel studio": "Write scripts and prepare faceless vertical videos.",
    "Story studio": "Create three branded Instagram Stories every day.",
    "Publishing": "Review scheduled posts and publishing activity.",
    "Analytics": "Measure content performance after connecting Instagram.",
    "Settings": "Configure your brand, AI services and Meta connection."
  };
  return descriptions[section] || "Manage your Instagram content workflow.";
}