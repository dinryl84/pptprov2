import { useState, useEffect } from "react";
import LandingHero from "./components/LandingHero";
import GeneratorForm from "./components/GeneratorForm";
import PaywallModal from "./components/PaywallModal";
import SampleModal from "./components/SampleModal";
import GeneratingModal from "./components/GeneratingModal";
import DownloadModal from "./components/DownloadModal";
import "./styles/global.css";

const API_BASE = import.meta.env.VITE_API_URL || "";
const STORAGE_KEY = "pptpro_download";
const PENDING_KEY = "pptpro_pending_ref";

export default function App() {
  const [showPaywall, setShowPaywall]       = useState(false);
  const [showSample, setShowSample]         = useState(false);
  const [showGenerating, setShowGenerating] = useState(false);
  const [showDownload, setShowDownload]     = useState(false);
  const [formData, setFormData]             = useState(null);
  const [error, setError]                   = useState("");

  const [dlInfo, setDlInfo] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch (_) {}
    return null;
  });

  const saveDlInfo = (info) => {
    setDlInfo(info);
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(info)); } catch (_) {}
  };

  const clearDlInfo = () => {
    setDlInfo(null);
    try { localStorage.removeItem(STORAGE_KEY); } catch (_) {}
  };

  // ── On mount: check if returning from PayMongo payment redirect ─────────────
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const paymentStatus = params.get("payment");
    const ref = params.get("ref");

    // Clean URL immediately regardless of outcome
    if (paymentStatus || ref) {
      window.history.replaceState({}, "", window.location.pathname);
    }

    if (paymentStatus === "success" && ref) {
      // Payment confirmed — start polling for generation result
      localStorage.removeItem(PENDING_KEY);
      setShowGenerating(true);
      pollForResult(ref);
    } else if (paymentStatus === "failed" || paymentStatus === "cancelled") {
      setError("Payment was cancelled or failed. Please try again.");
    } else if (dlInfo?.token) {
      // Existing completed download
      setShowDownload(true);
    }
  }, []);

  // ── Poll backend until generation is complete ──────────────────────────────
  const pollForResult = async (ref) => {
    const MAX_ATTEMPTS = 40;  // 40 × 5s = ~3.3 minutes max
    let attempts = 0;

    const poll = async () => {
      attempts++;
      try {
        const res = await fetch(`${API_BASE}/api/payment-status/${ref}`);
        if (!res.ok) throw new Error("Status check failed");
        const data = await res.json();

        if (data.status === "ready") {
          saveDlInfo({
            token:   data.token,
            has_pdf: data.has_pdf,
            title:   data.title,
            subject: data.subject,
          });
          setShowGenerating(false);
          setShowDownload(true);
          return;
        }

        if (data.status === "failed") {
          setShowGenerating(false);
          setError("Generation failed after payment. Please contact support with ref: " + ref);
          return;
        }

        // Still processing — keep polling
        if (attempts < MAX_ATTEMPTS) {
          setTimeout(poll, 5000);
        } else {
          setShowGenerating(false);
          setError("Generation is taking too long. Please contact support with ref: " + ref);
        }
      } catch (e) {
        if (attempts < MAX_ATTEMPTS) {
          setTimeout(poll, 5000);
        } else {
          setShowGenerating(false);
          setError("Could not check generation status. Contact support with ref: " + ref);
        }
      }
    };

    poll();
  };

  // Warn before closing during generation
  useEffect(() => {
    const handleUnload = (e) => {
      if (showGenerating) { e.preventDefault(); e.returnValue = ""; }
    };
    window.addEventListener("beforeunload", handleUnload);
    return () => window.removeEventListener("beforeunload", handleUnload);
  }, [showGenerating]);

  const handleGenerate = (data) => {
    setError("");
    setFormData(data);
    setShowPaywall(true);
  };

  const handleDownloadPPTX = () => {
    if (!dlInfo?.token) return;
    window.location.href = `${API_BASE}/api/download/${dlInfo.token}/pptx`;
  };

  const handleDownloadPDF = () => {
    if (!dlInfo?.token) return;
    window.location.href = `${API_BASE}/api/download/${dlInfo.token}/pdf`;
  };

  const handleCloseDownload = () => {
    setShowDownload(false);
    clearDlInfo();
  };

  return (
    <div className="app">
      <nav className="navbar">
        <a className="nav-brand" href="/">
          <div className="nav-logo">🎓</div>
          <span className="nav-title">ppt<span>Pro</span></span>
        </a>
        <div className="nav-right">
          {dlInfo?.token && !showDownload && (
            <button className="btn-primary" onClick={() => setShowDownload(true)}>
              ⬇ My Downloads
            </button>
          )}
          <button className="btn-ghost" onClick={() => setShowSample(true)}>
            👁️ See Sample
          </button>
        </div>
      </nav>

      <main>
        <LandingHero onSample={() => setShowSample(true)} />
        <GeneratorForm onGenerate={handleGenerate} />

        {error && (
          <div className="error-banner">
            <div className="error-inner">
              <span>⚠️</span>
              <span style={{ flex: 1 }}>{error}</span>
              <button onClick={() => setError("")}>✕</button>
            </div>
          </div>
        )}
      </main>

      <footer className="footer">
        🇵🇭 Made for Filipino Students &nbsp;•&nbsp; pptPro © 2025 &nbsp;•&nbsp; Powered by AI
      </footer>

      {showPaywall && formData && (
        <PaywallModal
          onClose={() => setShowPaywall(false)}
          title={formData.title}
          wantPDF={formData.wantPDF}
          formData={formData}
        />
      )}

      {showSample && <SampleModal onClose={() => setShowSample(false)} />}

      {showGenerating && (
        <GeneratingModal
          subject={formData?.subject}
          title={formData?.title}
          wantPDF={formData?.wantPDF}
        />
      )}

      {showDownload && dlInfo && (
        <DownloadModal
          title={dlInfo.title}
          subject={dlInfo.subject}
          hasPDF={dlInfo.has_pdf}
          onDownloadPPTX={handleDownloadPPTX}
          onDownloadPDF={handleDownloadPDF}
          onClose={handleCloseDownload}
        />
      )}
    </div>
  );
}
