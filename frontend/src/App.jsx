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

  const generateDraft = () => {
    const cleanTopic = topic.trim().replace(/[\s"'”’]+$/g, "").replace(/^[\s"'“‘]+/g, "");
    if (cleanTopic.length < 4) {
      setError("Please enter a topic with at least 4 characters.");
      return;
    }
    setError("");

    const isMinimumDue = /credit\s*card/i.test(cleanTopic) && /minimum\s*due/i.test(cleanTopic);
    let opening;
    let body;

    if (isMinimumDue) {
      opening = format === "Myth vs fact"
        ? "Credit card ka sirf Minimum Due bhar diya, toh kya aapka poora bill clear ho gaya? Nahi."
        : format === "3 quick points"
        ? "Credit card ka Minimum Due bharte waqt ye 3 baatein yaad rakho."
        : "Credit card bill mein Minimum Due bharna easy lagta hai, lekin iska matlab bill khatam hona nahi hai.";
      body = duration === "60 seconds"
        ? "\n\n1. Minimum Due, total outstanding amount ka sirf ek hissa hota hai.\n2. Due date tak Minimum Due pay karne se late-payment consequences se bachne mein madad mil sakti hai, lekin baaki balance unpaid rehta hai.\n3. Bache hue balance par card issuer ke terms ke mutabik finance charges/interest lag sakta hai. Interest-free period bhi affect ho sakta hai.\n\nExample: Agar total bill ₹10,000 hai aur aap sirf ₹500 Minimum Due pay karte hain, toh baaki ₹9,500 automatically maaf nahi hota. Exact charges apne card statement aur issuer ke MITC mein check karein."
        : "\n\nMinimum Due total bill ka sirf ek chhota hissa hota hai.\nAap ise pay kar do, tab bhi baaki outstanding amount clear nahi hota.\nBache hue balance par card ke terms ke hisaab se interest/finance charges lag sakte hain.\nIsliye possible ho toh total bill due date tak pay karo.";
    } else {
      opening = format === "Myth vs fact"
        ? `Kya aapko lagta hai ki ${cleanTopic} ke baare mein jo popular baat kahi jaati hai, woh hamesha sahi hoti hai? Zaroori nahi.`
        : format === "Explainer"
        ? `Aaj simple language mein samajhte hain: ${cleanTopic}.`
        : `Agar aap ${cleanTopic} ko lekar confused hain, ye 3 baatein samajh lijiye.`;
      body = duration === "60 seconds"
        ? `\n\nPoint 1: ${cleanTopic} ka basic concept aur meaning samjhein.\nPoint 2: Iska practical impact ek simple real-life example se dekhein.\nPoint 3: Apni situation par apply karne se pehle current rules, dates aur official source verify karein.`
        : `\n\nPehli baat: ${cleanTopic} ka basic concept samjhein.\nDoosri baat: iska practical impact apni situation par check karein.\nTeesri baat: action lene se pehle latest official guidance verify karein.`;
    }

    const ending = "\n\nSave this Reel, aur aise practical finance explainers ke liye follow karein.";
    setScript(`[HOOK]\n${opening}\n\n[EXPLANATION]${body}\n\n[CTA]${ending}`);
    const captionText = isMinimumDue
      ? "Minimum Due pay karna full credit card bill clear karne ke barabar nahi hai. Remaining balance par charges lag sakte hain—apne issuer ke latest terms aur statement check karein."
      : `${cleanTopic}: simple Hinglish explainer. Verify current rules and official guidance before acting.`;
    setCaption(`${captionText}\n\n#CreditCard #PersonalFinance #FinanceEducation #MoneyTips #India`);
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
        <button className="primary-btn studio-generate" onClick={generateDraft}><Sparkles size={17}/> Create script draft</button>
        <p className="studio-disclaimer">This is a template-based draft, not AI-generated or tax-verified content. Verify every legal, tax and financial claim against current official sources before publishing.</p>
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