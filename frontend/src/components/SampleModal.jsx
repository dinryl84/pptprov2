import { useState } from "react";

const SAMPLE_SLIDES = [
  {
    id: 1,
    label: "Title Slide",
    bg: "#0d1b2e",
    content: (
      <div style={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: "6% 8%", position: "relative", background: "linear-gradient(135deg,#0d1b2e,#0a2744)" }}>
        <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: "2.5%", background: "#f0b429" }} />
        <div style={{ background: "rgba(255,255,255,0.04)", border: "1.5px solid #f0b429", borderRadius: "8px", padding: "6% 8%", width: "85%", textAlign: "center" }}>
          <h1 style={{ color: "#fff", fontSize: "clamp(0.9rem,3.2vw,1.8rem)", fontWeight: 800, marginBottom: "4%", lineHeight: 1.15, fontFamily: "Georgia,serif" }}>Methodology of Research</h1>
          <div style={{ height: "1px", background: "#f0b429", margin: "0 10% 4%" }} />
          <p style={{ color: "#8b9fc5", fontSize: "clamp(0.45rem,1.4vw,0.75rem)" }}>Research Methods · College Level</p>
          <div style={{ display: "inline-block", background: "#f0b429", color: "#0d1b2e", padding: "1.5% 6%", borderRadius: "4px", marginTop: "4%", fontWeight: 700, fontSize: "clamp(0.38rem,1.1vw,0.62rem)" }}>
            {new Date().toLocaleDateString("en-PH", { year: "numeric", month: "long", day: "numeric" })}
          </div>
        </div>
        <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: "8%", background: "rgba(255,255,255,0.03)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <span style={{ color: "#4b5e80", fontSize: "clamp(0.28rem,0.85vw,0.5rem)" }}>🎓 pptPro — AI-Powered Academic Presentations for Filipino Students</span>
        </div>
      </div>
    ),
  },
  {
    id: 2,
    label: "Key Terms",
    bg: "white",
    content: (
      <div style={{ height: "100%", display: "flex", flexDirection: "column", background: "white" }}>
        <div style={{ background: "#003366", padding: "2.5% 4%", flexShrink: 0 }}>
          <span style={{ color: "white", fontWeight: 700, fontSize: "clamp(0.55rem,1.8vw,1rem)" }}>📖 Key Terms & Definitions</span>
        </div>
        <div style={{ flex: 1, padding: "2% 3.5%", display: "flex", flexDirection: "column", gap: "1.5%", overflow: "hidden" }}>
          {[
            ["Research Methodology", "The systematic framework of principles and procedures used to conduct research."],
            ["Quantitative Research", "Focuses on numerical data and statistical analysis to test hypotheses objectively."],
            ["Qualitative Research", "Explores non-numerical data to understand concepts, opinions, and experiences."],
          ].map(([term, def], i) => (
            <div key={i} style={{ background: "#d2e4ff", border: "1.2px solid #003366", borderRadius: "5px", padding: "2% 3%", fontSize: "clamp(0.34rem,1vw,0.58rem)", color: "#1a1a1a" }}>
              <strong>{term}:</strong> {def}
            </div>
          ))}
        </div>
        <div style={{ padding: "1% 3.5%", borderTop: "1px solid #eee", fontSize: "clamp(0.28rem,0.75vw,0.44rem)", color: "#aaa" }}>pptPro | For Educational Use Only</div>
      </div>
    ),
  },
  {
    id: 3,
    label: "Comparison",
    bg: "white",
    content: (
      <div style={{ height: "100%", display: "flex", flexDirection: "column", background: "white" }}>
        <div style={{ background: "#003366", padding: "2.5% 4%", flexShrink: 0 }}>
          <span style={{ color: "white", fontWeight: 700, fontSize: "clamp(0.55rem,1.8vw,1rem)" }}>⚖️ Quantitative vs Qualitative</span>
        </div>
        <div style={{ flex: 1, display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2%", padding: "2% 3%" }}>
          <div style={{ background: "#d2e4ff", border: "1.2px solid #003366", borderRadius: "6px", padding: "3%", fontSize: "clamp(0.32rem,0.95vw,0.56rem)", color: "#1a1a1a" }}>
            <strong style={{ display: "block", marginBottom: "3%", color: "#003366", fontSize: "clamp(0.38rem,1.1vw,0.62rem)" }}>📊 Quantitative</strong>
            {["✓ Uses numbers & statistics", "✓ Larger sample sizes", "✓ Objective measurement", "✓ Surveys & experiments"].map((x, i) => <div key={i} style={{ marginBottom: "2%" }}>{x}</div>)}
          </div>
          <div style={{ background: "#dcf5e7", border: "1.2px solid #006e3c", borderRadius: "6px", padding: "3%", fontSize: "clamp(0.32rem,0.95vw,0.56rem)", color: "#1a1a1a" }}>
            <strong style={{ display: "block", marginBottom: "3%", color: "#006e3c", fontSize: "clamp(0.38rem,1.1vw,0.62rem)" }}>💬 Qualitative</strong>
            {["✓ Uses words & meanings", "✓ Smaller focused samples", "✓ Subjective interpretation", "✓ Interviews & observations"].map((x, i) => <div key={i} style={{ marginBottom: "2%" }}>{x}</div>)}
          </div>
        </div>
        <div style={{ padding: "1% 3.5%", borderTop: "1px solid #eee", fontSize: "clamp(0.28rem,0.75vw,0.44rem)", color: "#aaa" }}>pptPro | For Educational Use Only</div>
      </div>
    ),
  },
  {
    id: 4,
    label: "Misconceptions",
    bg: "white",
    content: (
      <div style={{ height: "100%", display: "flex", flexDirection: "column", background: "white" }}>
        <div style={{ background: "#003366", padding: "2.5% 4%", flexShrink: 0 }}>
          <span style={{ color: "white", fontWeight: 700, fontSize: "clamp(0.55rem,1.8vw,1rem)" }}>⚠️ Common Misconceptions</span>
        </div>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "2%", padding: "2% 3%" }}>
          {[
            ["✗  Quantitative is always more reliable than qualitative", "✓  Both methods have equal scientific validity depending on the research question"],
            ["✗  Qualitative research is just interviews and surveys", "✓  It includes observations, case studies, focus groups, and document analysis"],
            ["✗  Mixed methods just means doing both separately", "✓  True mixed methods integrates both approaches to strengthen findings"],
          ].map(([err, ok], i) => (
            <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5%" }}>
              <div style={{ background: "#ffe0e0", border: "1px solid #b42828", borderRadius: "4px", padding: "2% 2.5%", fontSize: "clamp(0.3rem,0.88vw,0.52rem)", color: "#820000" }}>{err}</div>
              <div style={{ background: "#dcf5e7", border: "1px solid #006e3c", borderRadius: "4px", padding: "2% 2.5%", fontSize: "clamp(0.3rem,0.88vw,0.52rem)", color: "#004d28" }}>{ok}</div>
            </div>
          ))}
        </div>
        <div style={{ padding: "1% 3.5%", borderTop: "1px solid #eee", fontSize: "clamp(0.28rem,0.75vw,0.44rem)", color: "#aaa" }}>pptPro | For Educational Use Only</div>
      </div>
    ),
  },
  {
    id: 5,
    label: "References",
    bg: "white",
    content: (
      <div style={{ height: "100%", display: "flex", flexDirection: "column", background: "white" }}>
        <div style={{ background: "#21295c", padding: "2.5% 4%", flexShrink: 0 }}>
          <span style={{ color: "white", fontWeight: 700, fontSize: "clamp(0.55rem,1.8vw,1rem)" }}>📚 References (APA 7th Edition)</span>
        </div>
        <div style={{ flex: 1, padding: "2.5% 4%", display: "flex", flexDirection: "column", gap: "2.5%", overflow: "hidden" }}>
          {[
            "Creswell, J. W., & Creswell, J. D. (2018). Research design: Qualitative, quantitative, and mixed methods approaches (5th ed.). SAGE Publications.",
            "Bryman, A. (2016). Social research methods (5th ed.). Oxford University Press.",
            "Department of Education Philippines. (2023). K to 12 curriculum guide for research. DepEd.",
            "Punch, K. F. (2014). Introduction to social research (3rd ed.). SAGE Publications.",
            "Commission on Higher Education. (2022). Policies and standards for undergraduate research. CHED.",
          ].map((ref, i) => (
            <div key={i} style={{ fontSize: "clamp(0.28rem,0.85vw,0.5rem)", lineHeight: 1.5, color: "#1a1a1a", paddingLeft: "1em", textIndent: "-1em" }}>{ref}</div>
          ))}
        </div>
        <div style={{ padding: "1% 3.5%", borderTop: "1px solid #eee", fontSize: "clamp(0.28rem,0.75vw,0.44rem)", color: "#aaa" }}>pptPro | APA 7th Edition Format</div>
      </div>
    ),
  },
];

export default function SampleModal({ onClose }) {
  const [current, setCurrent] = useState(0);
  const slide = SAMPLE_SLIDES[current];

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box sample-modal">
        <div className="sample-header">
          <h2>👁️ Sample — Research Methods (College)</h2>
          <button className="modal-close" onClick={onClose} style={{ position: "static" }}>✕</button>
        </div>

        <div className="sample-body">
          {/* Slide viewer */}
          <div className="slide-viewer" style={{ background: slide.bg }}>
            <div className="slide-preview">{slide.content}</div>
          </div>

          {/* Nav */}
          <div className="slide-nav">
            <button
              className="slide-nav-btn"
              onClick={() => setCurrent((c) => c - 1)}
              disabled={current === 0}
            >← Prev</button>
            <span className="slide-counter">
              {current + 1} / {SAMPLE_SLIDES.length} · <span style={{ color: "var(--silver)" }}>{slide.label}</span>
            </span>
            <button
              className="slide-nav-btn"
              onClick={() => setCurrent((c) => c + 1)}
              disabled={current === SAMPLE_SLIDES.length - 1}
            >Next →</button>
          </div>

          {/* Thumbnails */}
          <div className="thumbs">
            {SAMPLE_SLIDES.map((s, i) => (
              <div
                key={s.id}
                className={`thumb ${i === current ? "active" : ""}`}
                onClick={() => setCurrent(i)}
                style={{ background: s.bg }}
                title={s.label}
              />
            ))}
          </div>
        </div>

        <div className="sample-cta">
          <p>✨ Your generated report will have 20–25 slides at this quality level!</p>
          <button className="btn-primary" onClick={onClose} style={{ padding: "0.65rem 1.5rem", fontSize: "0.9rem" }}>
            🚀 Generate mine — ₱20 only
          </button>
        </div>
      </div>
    </div>
  );
}
