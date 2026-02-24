



import { useState, useRef, useEffect } from "react";

const API_BASE_URL = "http://localhost:8000";

// ── Data ─────────────────────────────────────────────────────────────────────
const COURSE_COLORS = {
  "MATH 101": { fg: "#c9a84c", bg: "rgba(201,168,76,0.12)", bd: "rgba(201,168,76,0.3)" },
  "CS 201": { fg: "#a78bfa", bg: "rgba(167,139,250,0.12)", bd: "rgba(167,139,250,0.3)" },
  "PHYS 301": { fg: "#34d399", bg: "rgba(52,211,153,0.12)", bd: "rgba(52,211,153,0.3)" },
  "CHEM 202": { fg: "#fb923c", bg: "rgba(251,146,60,0.12)", bd: "rgba(251,146,60,0.3)" },
  "GENERAL": { fg: "#94a3b8", bg: "rgba(148,163,184,0.1)", bd: "rgba(148,163,184,0.25)" },
};

const INITIAL_MESSAGES = [
  {
    id: 1, role: "assistant",
    text: "Welcome. I am your private academic intelligence, trained exclusively on your institution's course materials. Every answer I provide is anchored to your uploaded knowledge base — no external data, no hallucination.\n\nAsk me anything covered in your syllabi, lecture notes, or course documents.",
    sources: [], confidence: null,
  },
];

// ── Particle Canvas ───────────────────────────────────────────────────────────
function ParticleField() {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    let raf;
    const resize = () => { canvas.width = canvas.offsetWidth; canvas.height = canvas.offsetHeight; };
    resize();
    window.addEventListener("resize", resize);

    const COUNT = 55;
    const particles = Array.from({ length: COUNT }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 1.2 + 0.3,
      vx: (Math.random() - 0.5) * 0.18,
      vy: (Math.random() - 0.5) * 0.18,
      alpha: Math.random() * 0.5 + 0.1,
    }));

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach(p => {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(201,168,76,${p.alpha})`;
        ctx.fill();
      });

      // Draw soft connection lines
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 100) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(201,168,76,${0.06 * (1 - dist / 100)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", resize); };
  }, []);

  return <canvas ref={canvasRef} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }} />;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function parseText(text) {
  return text.split("\n").map((line, i) => {
    const key = i;
    if (!line.trim()) return <div key={key} style={{ height: 6 }} />;
    if (line.startsWith("- ")) {
      const inner = line.slice(2).replace(/\*\*(.*?)\*\*/g, (_, m) => `<strong style="color:#e8d5a3;font-weight:700">${m}</strong>`);
      return <li key={key} style={{ marginLeft: 18, marginBottom: 3, lineHeight: 1.75 }} dangerouslySetInnerHTML={{ __html: inner }} />;
    }
    const inner = line.replace(/\*\*(.*?)\*\*/g, (_, m) => `<strong style="color:#e8d5a3;font-weight:700">${m}</strong>`);
    return <p key={key} style={{ marginBottom: 4, lineHeight: 1.8 }} dangerouslySetInnerHTML={{ __html: inner }} />;
  });
}



function CourseTag({ course }) {
  const c = COURSE_COLORS[course] || COURSE_COLORS["GENERAL"];
  return (
    <span style={{ fontSize: 9.5, fontWeight: 800, letterSpacing: "0.07em", padding: "2px 8px", borderRadius: 4, background: c.bg, color: c.fg, border: `1px solid ${c.bd}` }}>
      {course}
    </span>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function NoirTutor() {
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [docs, setDocs] = useState([]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [tab, setTab] = useState("docs");
  const [openSource, setOpenSource] = useState(null);
  const [mounted, setMounted] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [apiError, setApiError] = useState("");
  const fileRef = useRef(null);
  const chatEnd = useRef(null);
  const textaRef = useRef(null);

  useEffect(() => {
    setTimeout(() => setMounted(true), 80);
    checkHealth();
  }, []);

  useEffect(() => {
    chatEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/health`);
      if (!res.ok) setApiError("Backend unavailable");
    } catch (err) {
      setApiError("Cannot connect to backend. Make sure it's running on port 8000.");
    }
  };

  const send = async () => {
    if (!input.trim() || typing) return;

    const userQuery = input.trim();
    setMessages(p => [...p, { id: Date.now(), role: "user", text: userQuery, sources: [], confidence: null }]);
    setInput("");
    setApiError("");
    if (textaRef.current) { textaRef.current.style.height = "24px"; }
    setTyping(true);

    try {
      const res = await fetch(`${API_BASE_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: userQuery,
          retrieval_top_k: 8,
          final_top_k: 4,
          use_cache: true,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to get answer");
      }

      const data = await res.json();
      const sources = (data.sources || []).map((src, idx) => ({
        id: idx,
        doc: src.doc || src,
        page: src.page || "—",
        snippet: src.snippet || src,
      }));

      setMessages(p => [...p, {
        id: Date.now() + 1,
        role: "assistant",
        text: data.answer || "No answer generated",
        sources: sources,
        confidence: null,
      }]);
    } catch (err) {
      setApiError(err.message || "Error processing query");
      setMessages(p => [...p, {
        id: Date.now() + 1,
        role: "assistant",
        text: `Error: ${err.message}. Please try again.`,
        sources: [],
        confidence: null,
      }]);
    } finally {
      setTyping(false);
    }
  };

  const onKey = e => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const uploadFiles = async (files) => {
    if (!files || files.length === 0) return;

    const pdfFiles = Array.from(files).filter(f => f.name.toLowerCase().endsWith(".pdf"));

    if (pdfFiles.length === 0) {
      setUploadError("Please upload only PDF files");
      return;
    }

    setUploading(true);
    setUploadError("");
    setApiError("");

    const formData = new FormData();
    pdfFiles.forEach(f => formData.append("files", f));

    // Add placeholder docs (and wipe old ones for Strict Replace Mode)
    const placeholders = pdfFiles.map(f => ({
      id: Date.now() + Math.random(),
      name: f.name.replace(/\.[^.]+$/, ""),
      ext: "PDF",
      course: "GENERAL",
      pages: "—",
      date: new Date().toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      status: "processing",
      size: (f.size / 1e6).toFixed(1) + " MB",
    }));

    // Reset UI to mirror Backend Strict Replace Mode Wipe
    setDocs(placeholders);
    setMessages(INITIAL_MESSAGES);

    try {
      const res = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed");
      }

      const result = await res.json();

      // Update docs to mark as indexed
      setDocs(p => p.map(d => {
        if (placeholders.some(ph => ph.id === d.id)) {
          const matchingKey = Object.keys(result.file_pages || {}).find(k => k.startsWith(d.name));
          const pages = matchingKey && result.file_pages ? result.file_pages[matchingKey] : 1;
          return { ...d, status: "indexed", pages };
        }
        return d;
      }));



      setTab("docs");
    } catch (err) {
      setUploadError(err.message || "Upload failed");
      // Remove placeholders on error
      setDocs(p => p.filter(d => !placeholders.some(ph => ph.id === d.id)));
    } finally {
      setUploading(false);
    }
  };

  const indexed = docs.filter(d => d.status === "indexed").length;
  const totalPg = docs.filter(d => d.pages !== "—").reduce((a, d) => a + (parseInt(d.pages) || 0), 0);

  // ── CSS ────────────────────────────────────────────────────────────────────
  const css = `
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=Outfit:wght@300;400;500;600;700&display=swap');

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --gold:       #c9a84c;
      --gold-light: #e8d5a3;
      --gold-dim:   rgba(201,168,76,0.15);
      --gold-glow:  rgba(201,168,76,0.08);
      --bg:         #080808;
      --bg2:        #0d0d0d;
      --glass:      rgba(255,255,255,0.03);
      --glass-bd:   rgba(255,255,255,0.07);
      --glass-hover:rgba(255,255,255,0.055);
      --text:       #d4cfc8;
      --text-dim:   rgba(212,207,200,0.45);
      --text-muted: rgba(212,207,200,0.25);
    }

    body { background: var(--bg); }

    ::-webkit-scrollbar { width: 3px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(201,168,76,0.2); border-radius: 2px; }

    /* Grain overlay */
    .grain::after {
      content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 999;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.035'/%3E%3C/svg%3E");
      background-size: 180px;
      opacity: 0.55;
    }

    .app {
      display: flex; height: 100vh; width: 100%; overflow: hidden; position: relative;
      font-family: 'Outfit', sans-serif; color: var(--text);
      background: radial-gradient(ellipse 80% 60% at 15% 0%, rgba(201,168,76,0.055) 0%, transparent 55%),
                  radial-gradient(ellipse 60% 40% at 90% 100%, rgba(201,168,76,0.04) 0%, transparent 50%),
                  var(--bg);
    }

    /* ── SIDEBAR ── */
    .sidebar {
      width: 280px; min-width: 280px; height: 100%;
      background: rgba(10,9,8,0.85);
      backdrop-filter: blur(24px) saturate(1.2);
      -webkit-backdrop-filter: blur(24px) saturate(1.2);
      border-right: 1px solid var(--glass-bd);
      display: flex; flex-direction: column;
      position: relative; z-index: 10;
      box-shadow: 1px 0 30px rgba(0,0,0,0.6);
    }

    .sb-brand {
      padding: 24px 20px 20px;
      border-bottom: 1px solid var(--glass-bd);
      flex-shrink: 0;
    }

    .brand-eyebrow {
      font-size: 9px; letter-spacing: 0.22em; color: var(--gold);
      text-transform: uppercase; font-weight: 600; margin-bottom: 6px;
    }
    .brand-name {
      font-family: 'Cormorant Garamond', serif;
      font-size: 26px; font-weight: 700; line-height: 1;
      color: var(--gold-light); letter-spacing: -0.01em;
    }
    .brand-sub {
      font-size: 10px; color: var(--text-muted); margin-top: 6px; line-height: 1.5; font-weight: 300;
    }

    .status-pill {
      display: inline-flex; align-items: center; gap: 5px;
      margin-top: 10px; padding: 4px 10px; border-radius: 20px;
      background: rgba(52,211,153,0.08); border: 1px solid rgba(52,211,153,0.2);
      font-size: 10px; color: #34d399; font-weight: 600; letter-spacing: 0.05em;
    }
    .status-dot { width: 5px; height: 5px; border-radius: 50%; background: #34d399; box-shadow: 0 0 6px #34d399; animation: glow-pulse 2s ease-in-out infinite; }

    .sb-tabs {
      display: flex; border-bottom: 1px solid var(--glass-bd); flex-shrink: 0;
    }
    .sb-tab {
      flex: 1; padding: 12px 0; text-align: center; cursor: pointer;
      font-size: 11px; font-weight: 600; letter-spacing: 0.07em; text-transform: uppercase;
      border: none; background: none; transition: all 0.2s; position: relative; color: var(--text-muted);
    }
    .sb-tab.active { color: var(--gold); }
    .sb-tab.active::after { content:''; position:absolute; bottom:-1px; left:20%; right:20%; height:1px; background:var(--gold); box-shadow: 0 0 8px var(--gold); }

    .doc-list { flex: 1; overflow-y: auto; padding: 10px; }

    .doc-card {
      padding: 11px 12px; border-radius: 10px; margin-bottom: 5px; cursor: pointer;
      background: var(--glass); border: 1px solid transparent;
      transition: all 0.2s ease; animation: fade-up 0.4s ease both;
    }
    .doc-card:hover { background: var(--glass-hover); border-color: var(--glass-bd); transform: translateX(2px); }

    .doc-name { font-size: 12.5px; font-weight: 500; color: #ccc; line-height: 1.35; margin-bottom: 5px; }
    .doc-meta { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 4px; }
    .doc-info { font-size: 10px; color: var(--text-muted); }

    .processing-bar {
      height: 2px; border-radius: 2px; background: rgba(255,255,255,0.06); margin-top: 6px; overflow: hidden;
    }
    .processing-fill {
      height: 100%; width: 40%; border-radius: 2px;
      background: linear-gradient(90deg, transparent, var(--gold), transparent);
      animation: shimmer 1.6s ease-in-out infinite;
    }

    .sb-stats {
      padding: 14px 20px; border-top: 1px solid var(--glass-bd); flex-shrink: 0;
      display: flex; justify-content: space-between;
    }
    .stat { text-align: center; }
    .stat-n { font-family: 'Cormorant Garamond', serif; font-size: 26px; font-weight: 700; color: var(--gold); line-height: 1; }
    .stat-l { font-size: 9px; color: var(--text-muted); letter-spacing: 0.1em; text-transform: uppercase; margin-top: 2px; font-weight: 500; }
    .stat-div { width: 1px; background: var(--glass-bd); }

    /* Upload */
    .upload-zone {
      margin: 14px; padding: 28px 20px; border-radius: 14px; text-align: center; cursor: pointer;
      border: 1px dashed var(--glass-bd); background: var(--glass); transition: all 0.25s;
    }
    .upload-zone.active { border-color: var(--gold); background: var(--gold-dim); }
    .upload-icon { font-size: 28px; margin-bottom: 10px; }
    .upload-title { font-size: 13px; font-weight: 600; color: #aaa; margin-bottom: 4px; }
    .upload-sub { font-size: 11px; color: var(--text-muted); margin-bottom: 14px; line-height: 1.5; }
    .upload-btn {
      padding: 8px 20px; border-radius: 8px; border: 1px solid var(--gold);
      background: var(--gold-dim); color: var(--gold); font-size: 12px; font-weight: 700;
      cursor: pointer; font-family: 'Outfit', sans-serif; letter-spacing: 0.04em;
      transition: all 0.2s;
    }
    .upload-btn:hover { background: rgba(201,168,76,0.25); }

    /* ── MAIN ── */
    .main { flex: 1; display: flex; flex-direction: column; overflow: hidden; position: relative; }

    .top-bar {
      height: 56px; padding: 0 28px; border-bottom: 1px solid var(--glass-bd);
      display: flex; align-items: center; justify-content: space-between;
      background: rgba(8,8,8,0.7); backdrop-filter: blur(20px); flex-shrink: 0; z-index: 5;
    }
    .top-title {
      font-family: 'Cormorant Garamond', serif; font-size: 17px; font-weight: 600;
      color: var(--gold-light); letter-spacing: 0.02em;
    }
    .top-badges { display: flex; gap: 8px; }
    .badge {
      padding: 4px 12px; border-radius: 20px; font-size: 10px; font-weight: 600; letter-spacing: 0.06em;
    }
    .badge-lock { background: rgba(255,255,255,0.04); border: 1px solid var(--glass-bd); color: var(--text-muted); }
    .badge-active { background: rgba(52,211,153,0.08); border: 1px solid rgba(52,211,153,0.25); color: #34d399; }

    /* Chat */
    .chat-scroll { flex: 1; overflow-y: auto; padding: 32px 0; }
    .chat-inner { max-width: 780px; margin: 0 auto; padding: 0 28px; }

    .msg-wrap { display: flex; margin-bottom: 24px; animation: fade-up 0.35s ease both; }
    .msg-wrap.user { justify-content: flex-end; }
    .msg-wrap.assistant { justify-content: flex-start; }

    .assistant-avatar {
      width: 32px; height: 32px; border-radius: 10px; flex-shrink: 0; margin-right: 12px; margin-top: 2px;
      background: linear-gradient(135deg, rgba(201,168,76,0.3), rgba(201,168,76,0.1));
      border: 1px solid rgba(201,168,76,0.3); display: flex; align-items: center; justify-content: center;
      font-size: 15px; box-shadow: 0 0 20px rgba(201,168,76,0.08);
    }

    .bubble {
      max-width: 640px; padding: 16px 20px; border-radius: 4px 18px 18px 18px;
      font-size: 14px; line-height: 1.7; position: relative;
    }
    .bubble.assistant {
      background: rgba(255,255,255,0.03);
      border: 1px solid var(--glass-bd);
      backdrop-filter: blur(12px);
      border-radius: 4px 18px 18px 18px;
      box-shadow: 0 4px 40px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);
    }
    .bubble.user {
      background: linear-gradient(135deg, rgba(201,168,76,0.18), rgba(201,168,76,0.09));
      border: 1px solid rgba(201,168,76,0.25);
      border-radius: 18px 4px 18px 18px;
      color: var(--gold-light);
      box-shadow: 0 4px 30px rgba(201,168,76,0.08);
      backdrop-filter: blur(12px);
    }

    .sender-label {
      font-size: 9.5px; letter-spacing: 0.14em; text-transform: uppercase;
      color: var(--gold); font-weight: 700; margin-bottom: 8px; display: flex; align-items: center; gap: 5px;
    }
    .sender-label::before { content: ''; display: inline-block; width: 16px; height: 1px; background: var(--gold); opacity: 0.5; }

    /* Source section */
    .sources-section { margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--glass-bd); }
    .sources-label { font-size: 9px; letter-spacing: 0.15em; text-transform: uppercase; color: rgba(201,168,76,0.6); font-weight: 700; margin-bottom: 8px; }
    .source-chip {
      display: inline-flex; align-items: center; gap: 5px; margin: 0 6px 6px 0;
      padding: 5px 12px; border-radius: 6px; cursor: pointer; font-size: 11px;
      border: 1px solid var(--glass-bd); background: var(--glass); color: var(--text-dim);
      transition: all 0.18s; font-weight: 500;
    }
    .source-chip:hover, .source-chip.open { border-color: rgba(201,168,76,0.4); background: var(--gold-dim); color: var(--gold-light); }
    .source-expand {
      margin-top: 8px; padding: 10px 14px; border-radius: 8px;
      border-left: 2px solid var(--gold); background: rgba(201,168,76,0.05);
      font-size: 12px; color: var(--text-dim); font-style: italic; line-height: 1.6;
      animation: fade-up 0.2s ease;
    }
    .source-ref { font-size: 10px; color: var(--text-muted); margin-top: 5px; font-style: normal; letter-spacing: 0.04em; }

    /* Typing */
    .typing-bubble {
      display: inline-flex; align-items: center; gap: 4px;
      padding: 14px 18px; border-radius: 4px 18px 18px 18px;
      background: var(--glass); border: 1px solid var(--glass-bd);
    }
    .tdot { width: 5px; height: 5px; border-radius: 50%; background: var(--gold); animation: tdot 1.3s ease-in-out infinite; }
    .tdot:nth-child(2) { animation-delay: 0.2s; }
    .tdot:nth-child(3) { animation-delay: 0.4s; }

    /* Input */
    .input-area { padding: 16px 28px 22px; border-top: 1px solid var(--glass-bd); background: rgba(8,8,8,0.8); backdrop-filter: blur(20px); flex-shrink: 0; }
    .input-wrap {
      max-width: 780px; margin: 0 auto; display: flex; align-items: flex-end; gap: 12px;
      background: rgba(255,255,255,0.03); border: 1px solid var(--glass-bd); border-radius: 16px;
      padding: 12px 14px 12px 18px; transition: border-color 0.2s, box-shadow 0.2s;
    }
    .input-wrap:focus-within { border-color: rgba(201,168,76,0.35); box-shadow: 0 0 0 3px rgba(201,168,76,0.06), 0 4px 30px rgba(0,0,0,0.5); }
    .chat-input {
      flex: 1; background: none; border: none; outline: none;
      color: var(--text); font-size: 14px; font-family: 'Outfit', sans-serif;
      resize: none; line-height: 1.6; min-height: 24px; max-height: 130px;
    }
    .chat-input::placeholder { color: var(--text-muted); }
    .send-btn {
      width: 38px; height: 38px; border-radius: 10px; border: none; cursor: pointer;
      background: linear-gradient(135deg, #c9a84c, #a07c2e);
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
      transition: all 0.2s; box-shadow: 0 2px 16px rgba(201,168,76,0.3);
    }
    .send-btn:hover { transform: scale(1.06); box-shadow: 0 4px 24px rgba(201,168,76,0.45); }
    .send-btn:disabled { background: rgba(255,255,255,0.05); box-shadow: none; cursor: default; transform: none; }
    .input-footer { text-align: center; font-size: 10.5px; color: var(--text-muted); margin-top: 10px; letter-spacing: 0.04em; max-width: 780px; margin-left: auto; margin-right: auto; }

    /* Decorative */
    .corner-decor {
      position: absolute; bottom: 60px; right: 40px; opacity: 0.04; pointer-events: none;
      font-family: 'Cormorant Garamond', serif; font-size: 160px; font-weight: 700; color: var(--gold);
      line-height: 1; user-select: none; letter-spacing: -0.05em;
    }

    /* Animations */
    @keyframes fade-up { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes shimmer { 0%,100% { transform: translateX(-200%); } 50% { transform: translateX(200%); } }
    @keyframes glow-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
    @keyframes tdot { 0%,80%,100% { transform: scale(0.6); opacity: 0.4; } 40% { transform: scale(1); opacity: 1; } }

    .page-enter { animation: fade-up 0.6s ease both; }
    .stagger-1 { animation-delay: 0.05s; }
    .stagger-2 { animation-delay: 0.12s; }
    .stagger-3 { animation-delay: 0.2s; }
    .stagger-4 { animation-delay: 0.28s; }
  `;

  return (
    <>
      <style>{css}</style>
      <div className="grain" />

      <div className="app">
        <ParticleField />

        {/* ── SIDEBAR ─────────────────────────────────────── */}
        <aside className="sidebar">
          <div className="sb-brand page-enter">
            <div className="brand-eyebrow">Private Academic Intelligence</div>
            <div className="brand-name">ScholArx</div>
            <div className="brand-sub">Knowledge-grounded Q&A · Zero external data · Your materials only</div>
          </div>

          <div className="sb-tabs">
            <button className={`sb-tab ${tab === "docs" ? "active" : ""}`} onClick={() => setTab("docs")}>Documents</button>
            <button className={`sb-tab ${tab === "upload" ? "active" : ""}`} onClick={() => setTab("upload")}>Upload</button>
          </div>

          {tab === "docs" ? (
            <div className="doc-list">
              {docs.length === 0 ? (
                <div style={{ padding: "24px 16px", textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>
                  No documents uploaded yet. Switch to the Upload tab to add files.
                </div>
              ) : (
                docs.map((doc, i) => (
                  <div key={doc.id} className="doc-card" style={{ animationDelay: `${i * 0.06}s` }}>
                    <div className="doc-name">{doc.name}</div>
                    <div className="doc-meta">
                      <CourseTag course={doc.course} />
                      <span style={{ fontSize: 10, color: doc.status === "indexed" ? "#34d399" : "#f59e0b", fontWeight: 600 }}>
                        {doc.status === "indexed" ? "● Indexed" : "◌ Processing"}
                      </span>
                    </div>
                    <div className="doc-info">
                      {doc.ext} · {doc.size}{doc.pages !== "—" ? ` · ${doc.pages} pp` : ""} · {doc.date}
                    </div>
                    {doc.status === "processing" && (
                      <div className="processing-bar"><div className="processing-fill" /></div>
                    )}
                  </div>
                ))
              )}
            </div>
          ) : (
            <div style={{ flex: 1, overflowY: "auto" }}>
              {uploadError && (
                <div style={{
                  margin: "14px", padding: "12px 16px", borderRadius: "10px",
                  background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
                  color: "#fca5a5", fontSize: "12px", animation: "fade-up 0.3s ease"
                }}>
                  ⚠ {uploadError}
                </div>
              )}
              <div
                className={`upload-zone ${dragOver ? "active" : ""}`}
                style={{ opacity: uploading ? 0.5 : 1, pointerEvents: uploading ? "none" : "auto" }}
                onClick={() => !uploading && fileRef.current?.click()}
                onDragOver={e => { e.preventDefault(); !uploading && setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={e => { e.preventDefault(); setDragOver(false); !uploading && uploadFiles(e.dataTransfer.files); }}
              >
                <div className="upload-icon">{uploading ? "⏳" : "📂"}</div>
                <div className="upload-title">{uploading ? "Processing..." : "Drop course materials here"}</div>
                <div className="upload-sub">{uploading ? "Your files are being uploaded and indexed..." : "PDF files only\nEmbedded into your private vector store"}</div>
                <button className="upload-btn" disabled={uploading}>{uploading ? "Uploading…" : "Browse Files"}</button>
                <input ref={fileRef} type="file" multiple accept=".pdf" style={{ display: "none" }} onChange={e => uploadFiles(e.target.files)} disabled={uploading} />
              </div>
              <div style={{ padding: "0 16px 16px", fontSize: 11, color: "var(--text-muted)", lineHeight: 1.8 }}>
                Files are chunked, embedded, and stored locally in your vector index. Nothing leaves your environment.
              </div>
            </div>
          )}


        </aside>

        {/* ── MAIN ─────────────────────────────────────────── */}
        <main className="main">


          <div className="top-bar">
            <div className="top-title">Academic Q&A</div>
            <div className="top-badges">
              <span className="badge badge-active">● {indexed} docs active</span>
            </div>
          </div>

          {/* Messages */}
          <div className="chat-scroll">
            <div className="chat-inner">
              {apiError && (
                <div style={{
                  margin: "16px 0", padding: "14px 20px", borderRadius: "12px",
                  background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
                  color: "#fca5a5", fontSize: "13px", maxWidth: "640px"
                }}>
                  <strong>⚠ Connection Error:</strong> {apiError}
                </div>
              )}
              {messages.map((msg, i) => {
                return (
                  <div key={msg.id} className={`msg-wrap ${msg.role}`} style={{ animationDelay: mounted ? "0s" : `${i * 0.07}s` }}>
                    {msg.role === "assistant" && (
                      <div className="assistant-avatar">🎓</div>
                    )}
                    <div className={`bubble ${msg.role}`}>
                      {msg.role === "assistant" && (
                        <div className="sender-label">ScholArx Intelligence</div>
                      )}
                      <ul style={{ listStyle: "disc", padding: 0 }}>
                        {parseText(msg.text)}
                      </ul>



                      {msg.sources?.length > 0 && (
                        <div className="sources-section">
                          <div className="sources-label">📎 Source Materials</div>
                          {msg.sources.map((s, si) => {
                            const key = `${msg.id}-${si}`;
                            const isOpen = openSource === key;
                            return (
                              <div key={si}>
                                <span className={`source-chip ${isOpen ? "open" : ""}`} onClick={() => setOpenSource(isOpen ? null : key)}>
                                  📄 {s.doc} {s.page !== "—" ? `· p.${s.page}` : ""} {isOpen ? "▲" : "▼"}
                                </span>
                                {isOpen && (
                                  <div className="source-expand">
                                    "{s.snippet}"
                                    <div className="source-ref">— {s.doc}</div>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}

              {typing && (
                <div className="msg-wrap assistant" style={{ animation: "fade-up 0.3s ease" }}>
                  <div className="assistant-avatar">🎓</div>
                  <div className="typing-bubble">
                    <div className="tdot" /><div className="tdot" /><div className="tdot" />
                  </div>
                </div>
              )}
              <div ref={chatEnd} />
            </div>
          </div>

          {/* Input */}
          <div className="input-area">
            <div className="input-wrap">
              <textarea
                ref={textaRef}
                className="chat-input"
                placeholder="Ask a question from your course materials…"
                value={input}
                rows={1}
                onChange={e => {
                  setInput(e.target.value);
                  e.target.style.height = "24px";
                  e.target.style.height = Math.min(e.target.scrollHeight, 130) + "px";
                }}
                onKeyDown={onKey}
              />
              <button className="send-btn" onClick={send} disabled={!input.trim() || typing}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
            </div>

          </div>
        </main>
      </div>
    </>
  );
}