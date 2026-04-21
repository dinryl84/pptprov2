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

export default function App() {
  const [showPaywall, setShowPaywall]       = useState(false);
  const [showSample, setShowSample]         = useState(false);
  const [showGenerating, setShowGenerating] = useState(false);
  const [showDownload, setShowDownload]     = useState(false);
  const [formData, setFormData]             = useState(null);
  const [error, setError]                   = useState("");

  // Token + metadata — persisted in localStorage so page refresh doesn't lose it
  const [dlInfo, setDlInfo] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch (_) {}
    return null;
  });

  // On mount: if we have a saved token, re-show download modal automatically
  useEffect(() => {
    if (dlInfo?.token) setShowDownload(true);
  }, []);

  const saveDlInfo = (info) => {
    setDlInfo(info);
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(info)); } catch (_) {}
  };

  const clearDlInfo = () => {
    setDlInfo(null);
    try { localStorage.removeItem(STORAGE_KEY); } catch (_) {}
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

  const handlePaymentConfirmed = async () => {
    setShowPaywall(false);
    setShowGenerating(true);
    setError("");

    try {
      const endpoint = formData.wantPDF ? "/api/generate/both" : "/api/generate";
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject:      formData.subject,
          level:        formData.level,
          title:        formData.title,
          language:     formData.language,
          instructions: formData.instructions || "",
        }),
      });

      if (!response.ok) {
        let detail = "Generation failed. Please try again.";
        try { const err = await response.json(); detail = err.detail || detail; } catch (_) {}
        throw new Error(detail);
      }

      const json = await response.json();
      saveDlInfo({
        token:   json.token,
        has_pdf: json.has_pdf,
        title:   formData.title,
        subject: formData.subject,
      });

      setShowGenerating(false);
      setShowDownload(true);
    } catch (e) {
      setError(e.message);
      setShowGenerating(false);
    }
  };

  // Downloads use direct URL navigation — browser handles the file, no blob needed
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
          {/* Persistent download button survives page resets */}
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

      {showPaywall && (
        <PaywallModal
          onClose={() => setShowPaywall(false)}
          onConfirm={handlePaymentConfirmed}
          title={formData?.title}
          wantPDF={formData?.wantPDF}
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
