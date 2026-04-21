# 🎓 pptPro v2 — AI PowerPoint Generator for Filipino Students

> Generate professional 20–25 slide PowerPoint presentations + Presenter Notes PDF in minutes for only ₱20.

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.11+
- DeepSeek API key (get free credits at platform.deepseek.com)

### 1. Backend Setup

```bash
cd backend
cp .env.example .env
# Edit .env and add your DEEPSEEK_API_KEY
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend: http://localhost:3000  
Backend:  http://localhost:8000

---

## 🔑 API Key Setup

Users do **NOT** need to enter any API keys. The key is stored server-side.

| Key | Where to Get | Cost |
|-----|-------------|------|
| **DeepSeek API Key** | platform.deepseek.com/api_keys | Very cheap (~$0.001/generation) |

Add to `backend/.env`:
```
DEEPSEEK_API_KEY=sk-your-key-here
```

---

## ☁️ Deployment

### Backend → Render

1. Push to GitHub
2. New Web Service on render.com
3. Build: `pip install -r backend/requirements.txt`
4. Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Add env var: `DEEPSEEK_API_KEY = your-key`

### Frontend → Vercel

1. New Project on vercel.com, root: `frontend`
2. Add env var: `VITE_API_URL = https://your-backend.onrender.com`

### Keep Backend Alive (Free Tier)

UptimeRobot → monitor `https://your-backend.onrender.com/health` every 5 min.

---

## 📊 What's Generated

- **PowerPoint (.pptx)** — 20–25 professionally designed slides
- **Presenter Notes (.pdf)** — Speaker notes for every slide (optional, +₱0 extra)

### Slide Types

Title, Table of Contents, Introduction, Background, Key Terms, Core Concepts (×3),
In-Depth Discussion, Types & Classifications, Philippine Examples, Comparison,
Pros/Cons, Misconceptions, Case Study, Trends, Challenges, Recommendations,
Discussion Questions, Key Takeaways, Conclusion, References (APA 7th).

---

## 🛠️ Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React 18 + Vite |
| Backend | FastAPI (Python 3.11) |
| AI | DeepSeek Chat (deepseek-chat) |
| PPTX | python-pptx |
| PDF | ReportLab |
| Deploy | Render + Vercel |

---

## 🇵🇭 Made with ❤️ for Filipino Students
