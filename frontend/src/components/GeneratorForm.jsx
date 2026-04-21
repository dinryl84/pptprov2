import { useState } from "react";

const SUBJECTS = [
  "Research Methods", "Methodology of Research", "Filipino", "English",
  "Mathematics", "Statistics", "Biology", "Chemistry", "Physics",
  "Earth Science", "History", "Araling Panlipunan", "Economics",
  "Business Studies", "Computer Science", "Technology & Livelihood",
  "Health", "Physical Education", "Values Education", "MAPEH",
  "Entrepreneurship", "Accounting", "Political Science", "Sociology",
  "Psychology", "Philosophy", "Literature", "Media & Information Literacy",
];

export default function GeneratorForm({ onGenerate }) {
  const [form, setForm] = useState({
    subject: "",
    level: "",
    title: "",
    language: "English",
    instructions: "",
    wantPDF: true,
  });
  const [errors, setErrors] = useState({});

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: "" }));
  };

  const validate = () => {
    const errs = {};
    if (!form.subject.trim()) errs.subject = "Subject is required";
    if (!form.level)          errs.level   = "Level is required";
    if (!form.title.trim())   errs.title   = "Report title is required";
    return errs;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    onGenerate({ ...form });
  };

  return (
    <section className="gen-section">
      <div className="gen-card">
        <div className="gen-card-header">
          <h2>Fill in your report details</h2>
          <p>All fields are required except Special Instructions.</p>
        </div>

        <div className="gen-card-body">
          <form onSubmit={handleSubmit}>
            <div className="field-grid">

              {/* Subject */}
              <div className="field">
                <label htmlFor="subject">Subject</label>
                <input
                  id="subject"
                  name="subject"
                  list="subjects-list"
                  value={form.subject}
                  onChange={handleChange}
                  placeholder="e.g. Research Methods"
                  autoComplete="off"
                  className={errors.subject ? "error" : ""}
                />
                <datalist id="subjects-list">
                  {SUBJECTS.map((s) => <option key={s} value={s} />)}
                </datalist>
                {errors.subject && <span className="field-error">{errors.subject}</span>}
                <span className="hint">Type or pick from the list</span>
              </div>

              {/* Level */}
              <div className="field">
                <label htmlFor="level">Education Level</label>
                <select
                  id="level"
                  name="level"
                  value={form.level}
                  onChange={handleChange}
                  className={errors.level ? "error" : ""}
                >
                  <option value="">Select level…</option>
                  <option value="JHS">Junior High School (JHS)</option>
                  <option value="SHS">Senior High School (SHS)</option>
                  <option value="College">College / University</option>
                  <option value="Graduate">Graduate School (Master's / PhD)</option>
                </select>
                {errors.level && <span className="field-error">{errors.level}</span>}
              </div>

              {/* Title */}
              <div className="field full">
                <label htmlFor="title">Report Title</label>
                <input
                  id="title"
                  name="title"
                  value={form.title}
                  onChange={handleChange}
                  placeholder="e.g. Methodology of Research: Quantitative vs Qualitative"
                  className={errors.title ? "error" : ""}
                />
                {errors.title && <span className="field-error">{errors.title}</span>}
              </div>

              {/* Language */}
              <div className="field">
                <label htmlFor="language">Language</label>
                <select id="language" name="language" value={form.language} onChange={handleChange}>
                  <option value="English">English</option>
                  <option value="Filipino">Filipino (Tagalog)</option>
                </select>
              </div>

              {/* Instructions */}
              <div className="field">
                <label htmlFor="instructions">
                  Special Instructions <span style={{ color: "var(--silver)", fontWeight: 400, textTransform: "none" }}>(optional)</span>
                </label>
                <textarea
                  id="instructions"
                  name="instructions"
                  value={form.instructions}
                  onChange={handleChange}
                  placeholder="Focus on quantitative methods, add more Philippine examples…"
                />
              </div>

            </div>

            {/* Download options */}
            <div style={{ marginTop: "1.25rem" }}>
              <label style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--silver)", letterSpacing: "0.04em", textTransform: "uppercase", display: "block", marginBottom: "0.5rem" }}>
                What to download
              </label>
              <div className="download-options">
                {/* PPTX is always included */}
                <div className="download-opt active" style={{ cursor: "default" }}>
                  <span className="download-opt-icon">📊</span>
                  <div className="download-opt-text">
                    <strong>PowerPoint (.pptx)</strong>
                    <span>20–25 slide deck · Always included</span>
                  </div>
                </div>

                {/* PDF toggle */}
                <label
                  className={`download-opt ${form.wantPDF ? "active" : ""}`}
                  style={{ cursor: "pointer" }}
                >
                  <span className="download-opt-icon">📄</span>
                  <div className="download-opt-text">
                    <strong>Presenter Notes (.pdf)</strong>
                    <span>Speaker notes for every slide</span>
                  </div>
                  <input
                    type="checkbox"
                    name="wantPDF"
                    checked={form.wantPDF}
                    onChange={handleChange}
                  />
                </label>
              </div>
            </div>

            <button type="submit" className="btn-generate">
              ✨ Generate My Presentation
              <span style={{
                background: "rgba(0,0,0,0.2)",
                padding: "0.2rem 0.6rem",
                borderRadius: "99px",
                fontSize: "0.85rem",
              }}>
                ₱20
              </span>
            </button>
          </form>
        </div>
      </div>
    </section>
  );
}
