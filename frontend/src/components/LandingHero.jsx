export default function LandingHero({ onSample }) {
  return (
    <>
      <section className="hero">
        <div className="hero-eyebrow">Ako ang mag ppt ikaw ang mag STUDY!</div>

        <h1>
          Generate your<br />
          <em>PowerPoint Report</em><br />
          in minutes
        </h1>

        <p className="hero-sub">
          Fill the form, pay ₱20, and get a professional 25–30 slide deck —
          complete with real APA references, academic content, and presenter notes.
          For JHS, SHS, College, and Graduate!
        </p>

        <div className="hero-stats">
          <div className="stat-pill"><strong>20–25</strong> Slides</div>
          <div className="stat-pill"><strong>₱20</strong> Flat Rate</div>
          <div className="stat-pill"><strong>APA 7th</strong> References</div>
          <div className="stat-pill"><strong>EN / FIL</strong> Language</div>
          <div className="stat-pill"><strong>PPTX + PDF</strong> Download</div>
        </div>
      </section>

      <div className="features">
        {[
          "🧠 AI-generated content",
          "📊 Professional layouts",
          "📚 Real references",
          "🗒️ Presenter notes",
          "📱 Mobile-friendly",
          "⚡ Ready in 3 mins",
        ].map((f) => (
          <div className="feature-chip" key={f}>{f}</div>
        ))}
      </div>
    </>
  );
}
