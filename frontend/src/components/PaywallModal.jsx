import { useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "";
const PRICE = 19;
const PRICE_CENTAVOS = 1900;

const PAYMENT_METHODS = [
  {
    id: "gcash",
    label: "GCash",
    desc: "Pay via GCash mobile wallet",
    bg: "linear-gradient(135deg,#007DFE,#0055CC)",
    icon: "G",
  },
  {
    id: "card",
    label: "Credit / Debit Card",
    desc: "Visa, Mastercard accepted",
    bg: "linear-gradient(135deg,#1a1a2e,#16213e)",
    icon: "💳",
  },
];

export default function PaywallModal({ onClose, title, wantPDF, formData }) {
  const [selected, setSelected]   = useState(null);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState("");

  const handlePay = async () => {
    if (!selected || loading) return;
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/api/create-payment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          amount:         PRICE_CENTAVOS,
          method:         selected,
          title:          title,
          want_pdf:       wantPDF,
          subject:        formData.subject,
          level:          formData.level,
          language:       formData.language,
          instructions:   formData.instructions || "",
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Payment setup failed. Please try again.");
      }

      const { checkout_url } = await res.json();
      // Redirect to PayMongo hosted checkout page
      window.location.href = checkout_url;

    } catch (e) {
      setError(e.message);
      setLoading(false);
    }
  };

  return (
    <div
      className="modal-overlay"
      onClick={(e) => e.target === e.currentTarget && !loading && onClose()}
    >
      <div className="modal-box" style={{ maxWidth: 420 }}>
        {!loading && (
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        )}

        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: "1.5rem" }}>
          <div style={{ fontSize: "2.2rem", marginBottom: "0.5rem" }}>📊</div>
          <h2 className="paywall-title">Unlock your presentation</h2>
          <p className="paywall-subtitle" style={{ maxWidth: 320, margin: "0.25rem auto 0" }}>
            "{title && title.length > 48 ? title.slice(0, 48) + "…" : title}"
          </p>
        </div>

        {/* Price box */}
        <div className="price-box" style={{ marginBottom: "1.25rem" }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "center", gap: "0.25rem" }}>
            <span style={{ fontSize: "1rem", color: "var(--gold)", fontWeight: 700 }}>₱</span>
            <span className="price">{PRICE}</span>
          </div>
          <div className="price-desc" style={{ marginTop: "0.25rem" }}>
            One-time · PPTX{wantPDF ? " + PDF Presenter Notes" : ""} · Instant download
          </div>
          <div style={{
            display: "flex",
            justifyContent: "center",
            gap: "0.5rem",
            marginTop: "0.6rem",
            flexWrap: "wrap",
          }}>
            {["20–25 slides", "APA 7th refs", "Presenter script", "EN / FIL"].map((f) => (
              <span key={f} style={{
                background: "rgba(240,180,41,0.1)",
                border: "1px solid rgba(240,180,41,0.2)",
                borderRadius: "99px",
                padding: "0.15rem 0.6rem",
                fontSize: "0.68rem",
                color: "var(--gold)",
                fontWeight: 600,
              }}>{f}</span>
            ))}
          </div>
        </div>

        {/* Payment methods */}
        <div className="pay-methods">
          {PAYMENT_METHODS.map(({ id, label, desc, bg, icon }) => (
            <button
              key={id}
              className={`pay-btn ${selected === id ? "selected" : ""}`}
              onClick={() => setSelected(id)}
              type="button"
              disabled={loading}
            >
              <div className="pay-logo" style={{ background: bg, fontSize: icon.length > 1 ? "1.1rem" : "0.78rem" }}>
                {icon}
              </div>
              <div className="pay-info">
                <strong>{label}</strong>
                <span>{desc}</span>
              </div>
              <div className="pay-radio" />
            </button>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div style={{
            background: "var(--red-dim)",
            border: "1px solid rgba(248,81,73,0.3)",
            borderRadius: "var(--radius-sm)",
            padding: "0.6rem 0.85rem",
            fontSize: "0.78rem",
            color: "#ff8080",
            marginBottom: "0.75rem",
          }}>
            ⚠️ {error}
          </div>
        )}

        {/* Pay button */}
        <button
          className="btn-pay-submit"
          onClick={handlePay}
          disabled={!selected || loading}
          style={selected === "gcash"
            ? { background: "linear-gradient(135deg,#007DFE,#0055CC)" }
            : selected === "card"
            ? { background: "linear-gradient(135deg,#3fb950,#2da44e)" }
            : undefined
          }
        >
          {loading
            ? "Redirecting to payment…"
            : selected
            ? `Pay ₱${PRICE} via ${selected === "gcash" ? "GCash" : "Card"}`
            : "Choose a payment method"}
        </button>

        <p className="pay-secure">
          🔒 Secure payment via PayMongo · SSL encrypted
        </p>
      </div>
    </div>
  );
}