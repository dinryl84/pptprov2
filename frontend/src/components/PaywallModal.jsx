import { useState } from "react";

export default function PaywallModal({ onClose, onConfirm, title, wantPDF }) {
  const [selected, setSelected] = useState(null);
  const [processing, setProcessing] = useState(false);

  const handlePay = () => {
    if (!selected) return;
    setProcessing(true);
    setTimeout(() => onConfirm(), 2500);
  };

  if (processing) {
    return (
      <div className="modal-overlay">
        <div className="modal-box" style={{ maxWidth: 400, textAlign: "center" }}>
          <div className="processing-wrap">
            <div className="processing-icon">
              {selected === "gcash" ? "💙" : "💚"}
            </div>
            <h3>Processing payment…</h3>
            <p style={{ marginTop: "0.4rem" }}>
              {selected === "gcash" ? "GCash" : "Maya"} — ₱20.00
            </p>
            <div className="prog-bar" style={{ marginTop: "1.5rem" }}>
              <div className="prog-fill" />
            </div>
            <p style={{ fontSize: "0.75rem", color: "var(--silver)", marginTop: "0.5rem" }}>
              Do not close this page
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box">
        <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>

        <div className="paywall-icon">📊</div>
        <h2 className="paywall-title">Unlock your report</h2>
        <p className="paywall-subtitle">
          "{title && title.length > 45 ? title.slice(0, 45) + "…" : title}"
        </p>

        <div className="price-box">
          <div className="price">₱20</div>
          <div className="price-desc">
            One-time payment · PPTX{wantPDF ? " + PDF Presenter Notes" : ""} · Instant download
          </div>
        </div>

        <div className="pay-methods">
          {[
            { id: "gcash", label: "GCash", desc: "Pay via GCash mobile wallet", bg: "#007DFE" },
            { id: "maya",  label: "Maya",  desc: "Pay via Maya (PayMaya)",      bg: "#00C065" },
          ].map(({ id, label, desc, bg }) => (
            <button
              key={id}
              className={`pay-btn ${selected === id ? "selected" : ""}`}
              onClick={() => setSelected(id)}
              type="button"
            >
              <div className="pay-logo" style={{ background: bg }}>
                {label[0]}
              </div>
              <div className="pay-info">
                <strong>{label}</strong>
                <span>{desc}</span>
              </div>
              <div className="pay-radio" />
            </button>
          ))}
        </div>

        <button
          className="btn-pay-submit"
          onClick={handlePay}
          disabled={!selected}
          style={selected === "maya" ? { background: "linear-gradient(135deg,#00C065,#009952)" } : undefined}
        >
          {selected
            ? `Pay ₱20 via ${selected === "gcash" ? "GCash" : "Maya"}`
            : "Choose a payment method"}
        </button>

        <p className="pay-secure">🔒 Secure payment via PayMongo · No card needed</p>
      </div>
    </div>
  );
}
