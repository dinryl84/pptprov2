export default function DownloadModal({
  title,
  subject,
  hasPDF,
  onDownloadPPTX,
  onDownloadPDF,
  onClose,
}) {
  const safeName = (title || "presentation").slice(0, 50);

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box download-modal">
        <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>

        <div className="dl-header">
          <div className="dl-icon">🎉</div>
          <h2>Your files are ready!</h2>
          <p>Click a button below to download. Links are valid for <strong>1 hour</strong>.</p>
        </div>

        <div className="dl-files">
          {/* PPTX */}
          <div className="dl-file">
            <span className="dl-file-icon">📊</span>
            <div className="dl-file-info">
              <strong>{safeName}_pptPro.pptx</strong>
              <span>
                {subject ? `${subject} · ` : ""}
                Open in PowerPoint or Google Slides
              </span>
            </div>
            <button className="dl-btn" onClick={onDownloadPPTX}>
              ⬇ Download
            </button>
          </div>

          {hasPDF && (
            <div className="dl-file">
              <span className="dl-file-icon">📄</span>
              <div className="dl-file-info">
                <strong>{safeName}_pptPro_Notes.pdf</strong>
                <span>Presenter notes · Speaker guide for every slide</span>
              </div>
              <button className="dl-btn" onClick={onDownloadPDF}>
                ⬇ Download
              </button>
            </div>
          )}
        </div>

        <div className="dl-actions">
          <button className="btn-dl-primary" onClick={onDownloadPPTX}>
            📊 Download PPTX
          </button>
          {hasPDF ? (
            <button
              className="btn-dl-primary"
              style={{ background: "linear-gradient(135deg,#388bfd,#1a68d4)" }}
              onClick={onDownloadPDF}
            >
              📄 Download PDF
            </button>
          ) : (
            <button className="btn-dl-secondary" onClick={onClose}>
              Close
            </button>
          )}
        </div>

        {hasPDF && (
          <button
            className="btn-dl-secondary"
            style={{ width: "100%", marginTop: "0.6rem" }}
            onClick={onClose}
          >
            Close
          </button>
        )}

        <p className="dl-note">
          ⏱ Links expire in 1 hour · ⚠️ Verify all AI-generated facts before submitting
        </p>
      </div>
    </div>
  );
}
