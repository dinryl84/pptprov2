import { useState, useEffect } from "react";

const STEPS = [
  { icon: "🧠", label: "AI is studying your topic…" },
  { icon: "📝", label: "Creating a 20–25 slide outline…" },
  { icon: "✍️", label: "Writing detailed content for each slide…" },
  { icon: "🔍", label: "Verifying references (APA 7th edition)…" },
  { icon: "🎨", label: "Applying professional layout and colors…" },
  { icon: "📊", label: "Building each PowerPoint slide…" },
  { icon: "🗒️", label: "Adding presenter notes…" },
  { icon: "📦", label: "Finalizing and packaging files…" },
];

export default function GeneratingModal({ subject, title, wantPDF }) {
  const [activeStep, setActiveStep] = useState(0);
  const [doneSteps, setDoneSteps] = useState([]);
  const [dots, setDots] = useState(".");

  useEffect(() => {
    const id = setInterval(() => {
      setActiveStep((prev) => {
        if (prev < STEPS.length - 1) {
          setDoneSteps((d) => [...d, prev]);
          return prev + 1;
        }
        return prev;
      });
    }, 2200);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const id = setInterval(() => {
      setDots((d) => (d.length >= 3 ? "." : d + "."));
    }, 500);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="modal-overlay" style={{ cursor: "not-allowed" }}>
      <div className="modal-box generating-box" style={{ cursor: "default" }}>
        <div className="gen-header">
          <div className="spinner" />
          <h2>Building your presentation{dots}</h2>
          {title && (
            <p className="gen-topic">
              "{title}" {subject ? `· ${subject}` : ""}
              {wantPDF ? " · PPTX + PDF" : ""}
            </p>
          )}
        </div>

        <ul className="gen-steps">
          {STEPS.map((step, i) => (
            <li
              key={i}
              className={`gen-step ${doneSteps.includes(i) ? "done" : i === activeStep ? "active" : ""}`}
            >
              <span className="gen-step-icon">
                {doneSteps.includes(i) ? "✅" : i === activeStep ? "⏳" : step.icon}
              </span>
              {step.label}
            </li>
          ))}
        </ul>

        <div className="gen-progress">
          <div className="gen-progress-fill" />
        </div>

        <div className="gen-warn">
          <span className="gen-warn-icon">⚠️</span>
          <div className="gen-warn-text">
            <strong>Do not close this tab!</strong>
            <span>
              This takes <strong>30–90 seconds</strong>. Closing will cancel generation.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
