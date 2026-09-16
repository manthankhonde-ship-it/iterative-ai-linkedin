# IteraAI (Web Version) — HTML/CSS/JS Frontend + FastAPI Backend

Same writer-reviewer LangGraph workflow as before, now split into a proper
**backend API** (Python/FastAPI) and a **real HTML/CSS/JS frontend** —
no Streamlit.

## How it works

```
Browser (index.html + script.js)
      |  fetch POST /generate {topic}
      v
FastAPI backend (main.py)
      |
      v
LangGraph workflow (itterative_tool.py)
   Writer (Mistral) -> Tavily search if needed -> Reviewer (Groq)
   -> approved, or rewrite (max 3 attempts)
      |
      v
JSON response { draft, attempt, is_approved, review_feedback }
      |
      v
script.js renders the result card
```

This version shows only the **final result** (no live step-by-step progress) —
one request, one response, kept simple on purpose.

## Project Structure

```
iterative-ai-web/
├── backend/
│   ├── main.py              (FastAPI app — /health, /generate)
│   ├── itterative_tool.py   (LangGraph workflow — same bug fix as before)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
└── .gitignore
```

## 1. Backend Setup (run this first)

```bash
cd backend
python -m venv .venv
```

Activate it:
- **Windows:** `.venv\Scripts\activate`
- **macOS/Linux:** `source .venv/bin/activate`

```bash
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and add your real `MISTRAL_API_KEY`, `GROQ_API_KEY`, `TAVILY_API_KEY`.

Run the API server:

```bash
uvicorn main:app --reload --port 8000
```

Check it's alive: open `http://localhost:8000/health` in your browser —
you should see `{"status":"ok","configured":true}`.

## 2. Frontend Setup

The frontend is plain HTML/CSS/JS — no build step, no npm needed.

Just open `frontend/index.html` directly in your browser (double-click it, or
right-click → Open With → your browser). It will call the backend at
`http://localhost:8000` by default.

If you want to serve it properly instead of using `file://`:

```bash
cd frontend
python -m http.server 5500
```

Then open `http://localhost:5500`.

## 3. Testing it end-to-end

1. Make sure the backend terminal shows `Uvicorn running on http://0.0.0.0:8000`.
2. Open the frontend. The sidebar should say **"AI Engine Online"**.
3. Type a topic, click **Generate Post**.
4. Watch the loading state, then the result card with the final post,
   iteration count, approval status, and reviewer feedback.
5. Try an empty topic — should show a validation message instead of calling the API.
6. Try stopping the backend server and clicking Generate — should show a
   friendly "Couldn't reach the AI backend" error, not a crash.

## 4. Deployment

You deploy the backend and frontend **separately**.

### Backend → Render.com (free tier)

1. Push this project to GitHub (see Git commands below).
2. Go to [render.com](https://render.com) → **New → Web Service**.
3. Connect your GitHub repo.
4. Set:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Under **Environment**, add your 3 secrets: `MISTRAL_API_KEY`, `GROQ_API_KEY`,
   `TAVILY_API_KEY`.
6. Deploy. Render gives you a URL like `https://iteraai-backend.onrender.com`.
7. Confirm `https://iteraai-backend.onrender.com/health` returns
   `{"status":"ok","configured":true}`.

### Frontend → Netlify / Vercel / GitHub Pages (any static host)

1. In `frontend/script.js`, change the top line:
   ```js
   const API_URL = "https://iteraai-backend.onrender.com";
   ```
   (use your actual Render URL from above)
2. Deploy the `frontend/` folder to Netlify (drag-and-drop the folder onto
   [app.netlify.com/drop](https://app.netlify.com/drop) is the fastest way),
   or Vercel, or GitHub Pages.
3. Open the deployed frontend URL and test the same flow as local testing.

> **CORS note:** the backend currently allows all origins (`allow_origins=["*"]`)
> so this works out of the box. For tighter security once you know your final
> frontend URL, change it in `backend/main.py` to that exact URL.

## Git Setup

```bash
git init
git add .
git commit -m "Initial commit - IteraAI web version"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

Before pushing, run `git status` and confirm `backend/.env` is **not** listed
(it's covered by `.gitignore`).

## Troubleshooting

**Sidebar says "Backend Unreachable"**
The FastAPI server isn't running, or `API_URL` in `script.js` doesn't match
where it's running. Check the terminal running `uvicorn` for errors.

**Sidebar says "Configuration Needed"**
Backend is running but `.env` is missing keys. Check `backend/.env` has all
3 keys filled in (locally) or Render's Environment tab has them (deployed).

**CORS error in browser console**
Only happens if you changed `allow_origins` in `main.py` to something that
doesn't match your actual frontend URL — double check it's an exact match
(including `https://` and no trailing slash).

**Generate button does nothing / stuck loading**
Open your browser's DevTools (F12) → Console tab, and check for a red error —
it usually points straight to the problem (wrong API_URL, backend down, etc).

## Verification Checklist

- [ ] Backend `/health` returns `configured: true`
- [ ] Frontend loads and shows "AI Engine Online"
- [ ] Generate produces a final post with feedback and iteration count
- [ ] Empty topic shows a validation message (no API call made)
- [ ] Backend down → frontend shows a friendly error, not a blank screen
- [ ] Copy / Download buttons work
- [ ] `backend/.env` is not committed to GitHub
- [ ] Backend deployed on Render, `/health` works on the public URL
- [ ] Frontend deployed, `API_URL` points to the deployed backend
- [ ] Full flow works on the public URLs
