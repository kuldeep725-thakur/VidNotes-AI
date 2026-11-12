# VidNotes AI

**Turn videos into knowledge.** Paste a YouTube link and get a summary, detailed study notes, important concepts, an MCQ quiz, exam-style questions and answers, and clickable timestamps, in both **English** and **Hinglish**. You can also export everything as a PDF, and plan your revision in a built-in **To-Do list**.

With the optional **accounts and cloud sync**, you sign in with Google or email and password, and your notes, quiz results, tasks and preferences follow you to every device.

- **Frontend:** React 19 + Vite, plain CSS with a design-token system, Lucide icons, Supabase Auth (supabase-js)
- **Backend:** FastAPI, Pydantic, SQLAlchemy, ReportLab, with SQLite (local) or Supabase Postgres (cloud)
- **AI and data:** [Supadata](https://supadata.ai) for transcripts and video details, [Google Gemini](https://ai.google.dev) for generation, with optional [Groq](https://groq.com) as a backup

### Two ways to run it

| | **Local mode** (default) | **Accounts & cloud sync** |
| --- | --- | --- |
| Sign-in | None, single user | Google or email/password (Supabase Auth) |
| Data stored in | `backend/data/vidnotes.db` (SQLite) | Your Supabase Postgres database |
| Other devices | No | Yes, sign in from any device |
| Setup | API keys only | API keys + a free Supabase project |

The app switches modes automatically: it runs in local mode until you add the Supabase settings to `backend/.env`.

---

## Requirements

| Tool | Version | Check with |
| --- | --- | --- |
| Python | **3.11 or newer** | `python --version` |
| Node.js | **20.19 or newer** (22 LTS recommended) | `node --version` |
| Gemini API key | free from [Google AI Studio](https://aistudio.google.com/apikey) | |
| Supadata API key | free from [supadata.ai](https://supadata.ai) | |
| Groq API key (optional) | free from [console.groq.com](https://console.groq.com/keys) | |
| Supabase project (optional, for accounts) | free from [supabase.com](https://supabase.com) | |

No Docker and no database server need to be installed. Local mode uses a single SQLite file; cloud mode uses Supabase's hosted database.

---

## Setup on Windows 10/11

Open **two** terminals (PowerShell or Command Prompt): one for the backend, one for the frontend.

### 1. Backend

```powershell
cd vidnotes-ai\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Open `backend\.env` in a text editor and paste your keys:

```env
GEMINI_API_KEY=your-gemini-api-key
SUPADATA_API_KEY=your-supadata-api-key
GROQ_API_KEY=your-groq-api-key   # optional backup, can be left empty
```

Start the server, still inside `backend` with the virtual environment active:

```powershell
uvicorn app.main:app --reload --port 8000
```

You should see `Application startup complete`. Check http://127.0.0.1:8000/api/health. Both `*_configured` values should be `true`.

> If PowerShell refuses to run `activate`, run this once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 2. Frontend

In the second terminal:

```powershell
cd vidnotes-ai\frontend
npm install
npm run dev
```

Open **http://localhost:5173**. This is local mode. To add sign-in and multi-device sync, continue with [Accounts & cloud sync](#accounts--cloud-sync-supabase).

### Starting it again later

```powershell
cd vidnotes-ai\backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

```powershell
cd vidnotes-ai\frontend
npm run dev
```

On macOS/Linux, use `source .venv/bin/activate` and `cp .env.example .env` instead.

> **Upgrading from an earlier version?** Run `pip install -r requirements.txt` and `npm install` again. On the first start the backend backs up your SQLite file to `backend/data/backups/` and then adds the new columns. All saved notes and tasks are kept.

---

## Accounts & cloud sync (Supabase)

Everything here uses Supabase's **free plan**. It takes about 15 minutes, and you only do it once.

### 1. Create the project

1. Sign in at [supabase.com](https://supabase.com/dashboard) and click **New project**.
2. Choose a name and a **database password**. Save the password: you need it in step 3.
3. Wait until the project is ready.

### 2. Create the tables and security rules

1. In the project, open **SQL Editor** → **New query**.
2. Open `supabase/migrations/20261108000000_vidnotes_schema.sql` from this project, copy everything, paste it in and click **Run**.

This creates the tables with **Row Level Security**, so each user can only ever read or change their own rows. It is safe to run again later.

### 3. Copy three values into `backend/.env`

| Variable | Where to find it in the Supabase Dashboard |
| --- | --- |
| `SUPABASE_URL` | **Settings → API Keys** (or the **Connect** dialog): the project URL, `https://<project-ref>.supabase.co` |
| `SUPABASE_PUBLISHABLE_KEY` | **Settings → API Keys** → the **publishable** key (`sb_publishable_…`) |
| `DATABASE_URL` | Click **Connect** → **Session pooler** → copy the URI and replace `[YOUR-PASSWORD]` with your database password |

```env
SUPABASE_URL=https://abcdefghijkl.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxxxxxxxxxxxxxxx
DATABASE_URL=postgresql://postgres.abcdefghijkl:YOUR-PASSWORD@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
```

- Use the **Session pooler** string. It works on home internet connections (IPv4); the "Direct connection" string needs IPv6, which many Windows PCs don't have.
- If your password contains special characters such as `@`, `#` or `/`, URL-encode them (for example `@` → `%40`), or choose a password with only letters and numbers.
- **Never use the secret key** (`sb_secret_…`) or the legacy `service_role` key. VidNotes doesn't need them. The publishable key is designed to be public: the backend sends it to the browser, which uses it only to sign in.

### 4. Tell Supabase where your app runs

**Authentication → URL Configuration**:

- **Site URL:** `http://localhost:5173`
- **Redirect URLs:** add `http://localhost:5173/**`

Password-reset and confirmation emails, and Google sign-in, only return to URLs on this list. When you deploy, add your real address as well (see [Deployment](#deployment)).

By default Supabase asks new users to **confirm their email** before they can log in. VidNotes shows a "Check your inbox" screen for this. You can switch it off under **Authentication → Sign In / Providers → Email → Confirm email**. Supabase's built-in email service sends only a few emails per hour, which is fine for personal use.

### 5. Restart the backend

Stop the backend (Ctrl+C) and start it again. http://127.0.0.1:8000/api/health should now show `"auth_enabled": true` and `"cloud_database": true`. Open http://localhost:5173: you'll see **Log in** and **Get Started**. Create your account.

If the backend stops with *"The Supabase database is missing tables"*, run step 2 first.

### Google sign-in (optional)

Email and password works without this. To add **Continue with Google**:

1. Open the [Google Cloud Console](https://console.cloud.google.com/) and create (or pick) a project.
2. Go to **Google Auth Platform**:
   - **Branding:** set the app name and support email.
   - **Audience:** choose **External** and, while testing, add your Google account as a test user.
   - **Data Access (Scopes):** make sure `openid`, `.../auth/userinfo.email` and `.../auth/userinfo.profile` are listed.
3. **Clients → Create client → Web application**:
   - **Authorized JavaScript origins:** `http://localhost:5173` (add your deployed address later).
   - **Authorized redirect URIs:** your Supabase callback URL, `https://<project-ref>.supabase.co/auth/v1/callback`. The exact URL is shown on Supabase's Google provider page.
   - Click **Create** and copy the **Client ID** and **Client secret**.
4. In Supabase, open **Authentication → Sign In / Providers → Google**, switch it on, paste the Client ID and Client secret, and save.

The Google client secret goes **only into the Supabase Dashboard**, never into this project's files. Your name and Google profile picture appear in VidNotes automatically.

### Move your existing local notes into your account

Your local SQLite notes are not uploaded automatically. To copy them into your account (after signing up once):

```powershell
cd vidnotes-ai\backend
.venv\Scripts\activate
python -m app.scripts.import_sqlite --email you@example.com --dry-run
python -m app.scripts.import_sqlite --email you@example.com
```

- `--dry-run` shows what would be imported and changes nothing.
- It copies every finished video (summary, notes, quiz, Q&A, both languages), quiz results and tasks.
- The SQLite file is **backed up first** to `backend/data/backups/` and only ever **read**: your local data stays exactly as it was.
- Videos already in your account and tasks already imported are skipped, so running it twice creates **no duplicates**.

To go back to local mode at any time, remove (or comment out with `#`) the three Supabase lines in `backend/.env` and restart the backend.

### How your data is protected

- The browser signs in with Supabase Auth and sends its access token to the backend with every request. The backend checks the token's signature against Supabase's public keys.
- Each request then runs in Postgres **as that user** (`authenticated` role with their user ID), so the database's Row Level Security policies apply to every query, not only the app's own filters.
- Composite foreign keys stop a task, quiz result or note from pointing at another user's video.
- Signed-out visitors (the `anon` role) have no access to any table.

---

## Configuration (`backend/.env`)

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Google Gemini key. Only the backend reads it. |
| `SUPADATA_API_KEY` | Supadata key for transcripts and video details. |
| `GEMINI_MODEL` | Main model, e.g. `gemini-3.5-flash`. |
| `GEMINI_FALLBACK_MODELS` | Comma-separated models, tried in order if the main one is busy, out of quota or retired. |
| `GEMINI_THINKING_LEVEL` | `minimal`, `low`, `medium` or `high`. Lower is faster. Leave empty for the model default. |
| `GROQ_API_KEY` | Optional. Enables Groq as a backup when Gemini is out of quota, busy or timing out. |
| `GROQ_MODEL` | Groq model with structured-output support, default `openai/gpt-oss-120b`. |
| `GROQ_REASONING_EFFORT` | `low`, `medium` or `high` for the gpt-oss models. |
| `SUPADATA_TRANSCRIPT_MODE` | `native` (existing captions only), `auto` (default: fall back to AI transcription) or `generate`. AI transcription uses more Supadata credits. |
| `CORS_ORIGINS` | Frontend origins allowed to call the API. Add your deployed frontend address here. |
| `SUPABASE_URL` | Optional. Your Supabase project URL. Setting it (with the key below) turns on accounts. |
| `SUPABASE_PUBLISHABLE_KEY` | Optional. The project's **publishable** key (public by design). Never the secret key. |
| `DATABASE_URL` | Optional. Supabase **Session pooler** connection string, for cloud storage and multi-device sync. Empty means local SQLite. |

Google retires model names over time. If you see *"The configured Gemini model is not available"*, set `GEMINI_MODEL` to a current model from [the model list](https://ai.google.dev/gemini-api/docs/models).

### About the Gemini free tier

Free-tier keys allow only about **20 requests per day per model**. One video uses:

- **Short video (under ~45 min):** 4 requests
- **Long video:** 2 requests per part plus 2 (e.g. a 4-hour course in 4 parts uses 10)

Because each model has its own daily quota, the fallback list adds capacity. When a model's daily quota runs out, the app skips it for an hour and uses the next one. If every model is exhausted, you get a clear message. For heavier use, enable billing on your Google AI Studio project.

### Groq backup (optional)

Gemini is always tried first. Only when every configured Gemini model is out of quota, overloaded or timing out does the app send that request to Groq. A wrong Gemini key or another configuration problem is still reported, not hidden.

Groq's **free tier allows about 8,000 tokens per minute, and that budget must cover both the request and the answer**. Because of that:

- The app watches Groq's rate-limit headers and waits for the budget to refill between requests. Expect pauses of up to a minute.
- On the free tier, Groq can produce full study material only for **short videos (roughly up to 5–10 minutes)**. For longer videos you'll see *"Groq's answer was cut off by your Groq plan's token limit"*. Groq's paid Developer tier raises the limit to 250,000 tokens per minute.

---

## How it works

```
YouTube URL ─► validate & extract video ID (no other URL is ever fetched)
           ─► Supadata: GET /v1/metadata and GET /v1/transcript for the canonical
                 youtube.com/watch?v=<id> URL (long or caption-less videos become an
                 async job, which is polled every second)
           ─► split into ~60k-character parts (never mid-line)
           ─► Gemini: detailed notes for each part (with section start times)
           ─► Gemini: summary, concepts, takeaways, timestamps, quiz, Q&A
                 (from the full transcript, or from the combined notes for long videos)
           ─► Gemini: Hinglish translation of the English material
                 (timestamps and correct answers are copied, not re-generated)
           ─► SQLite or Supabase Postgres, in one transaction
```

Every AI step goes through `ai_client.py`, which uses Gemini and switches to Groq only when Gemini is unavailable.

- Generation runs in the background. The page polls a status endpoint and shows live progress.
- Transcripts over ~600,000 characters (about 10 hours of speech) are rejected with an explanation, never silently truncated.
- Videos without a transcript fail with a clear message instead of made-up content.
- Analyzing the same video twice opens the saved notes instead of creating a duplicate. A failed video can be retried.
- If the server restarts mid-generation, that job is marked as interrupted. No data is deleted.

---

## Project structure

```
vidnotes-ai/
├── backend/
│   ├── app/
│   │   ├── api/videos.py              video and quiz-result routes
│   │   ├── api/todos.py               to-do routes
│   │   ├── api/users.py               profile and preferences routes
│   │   ├── api/deps.py                per-user database session
│   │   ├── core/auth.py               Supabase token verification
│   │   ├── core/config.py             settings from .env
│   │   ├── core/errors.py             user-facing error types
│   │   ├── models/types.py            shared column types (SQLite + Postgres)
│   │   ├── models/video.py            video tables
│   │   ├── models/todo.py             to-do table
│   │   ├── models/user.py             profiles, preferences, quiz results
│   │   ├── schemas/content.py         AI output shapes (also Gemini response schemas)
│   │   ├── schemas/video.py           video API request/response models
│   │   ├── schemas/todo.py            to-do API request/response models
│   │   ├── schemas/user.py            account API models
│   │   ├── services/
│   │   │   ├── supadata_client.py     transcripts + metadata, retries, error mapping
│   │   │   ├── ai_client.py           Gemini first, Groq backup
│   │   │   ├── gemini_client.py       structured generation, model fallback, error mapping
│   │   │   ├── groq_client.py         optional Groq backup, rate-limit pacing
│   │   │   ├── transcript_chunker.py  timestamped lines and chunking
│   │   │   ├── content_generator.py   prompts: notes, study pack, Hinglish
│   │   │   ├── video_processor.py     background pipeline
│   │   │   ├── video_service.py       database operations for videos
│   │   │   ├── todo_service.py        database operations for to-do tasks
│   │   │   ├── user_service.py        profiles, preferences, quiz results
│   │   │   └── pdf_service.py         ReportLab PDF export
│   │   ├── scripts/import_sqlite.py   copy local notes into a Supabase account
│   │   ├── utils/                     YouTube URL parsing, time formatting, SQLite backups
│   │   ├── database.py                engine, Row Level Security context, table setup
│   │   └── main.py                    app setup, CORS, size limit, error handlers
│   ├── data/                          SQLite database and backups/ (created automatically)
│   ├── tests/                         pytest suite (no real API calls)
│   ├── requirements.txt
│   └── .env.example
├── supabase/migrations/               cloud tables + Row Level Security (run once)
└── frontend/
    ├── src/
    │   ├── components/                UI pieces (results/ holds the five tab views)
    │   ├── context/AuthContext.jsx    sign-in state, profile, synced preferences
    │   ├── pages/                     Home, My Notes, Video, To-Do, Profile, About, and the sign-in pages
    │   ├── layouts/AppLayout.jsx      navbar + footer shell
    │   ├── services/api.js            all backend calls
    │   ├── hooks/                     useTheme, useVideo (polling)
    │   ├── styles/                    tokens.css (design system), animations.css, page styles
    │   └── utils/                     formatting, URL validation
    ├── index.html
    └── vite.config.js                 dev proxy: /api → http://127.0.0.1:8000
```

### Database tables

Every table that holds user data has a `user_id` column (the Supabase Auth user ID; in local mode, a fixed local ID).

| Table | Contents |
| --- | --- |
| `profiles` | Name, email and profile picture of each user |
| `user_preferences` | Theme, default notes language, default number of quiz questions |
| `videos` | Video history: URL, YouTube ID (unique per user), title, channel, thumbnail, duration, status, progress |
| `study_materials` | One row per language: summary, study notes, timestamps |
| `quiz_questions` | Question, four options, correct index, explanation, per language |
| `qa_pairs` | Exam questions and answers, per language |
| `quiz_results` | Every finished quiz attempt: score, total, chosen answers |
| `todos` | Study tasks: title, done flag, optional due date, optional link to a video |

Deleting a video removes its notes, quiz, Q&A and quiz results (cascade), but **keeps** to-do tasks linked to it and only removes the link. Deleting a Supabase user removes all their data.

**Local mode:** the database file is `backend/data/vidnotes.db`. New tables and columns are added automatically on startup after a backup is made; existing records are never deleted. **Cloud mode:** the tables are created by the SQL file in `supabase/migrations/`.

### Backups

- Before upgrading or importing, the backend copies the SQLite file to `backend/data/backups/vidnotes-<reason>-<date>.db`. To restore one, stop the backend and copy it back over `backend/data/vidnotes.db`.
- Supabase lets you restore daily backups from **Database → Backups** on its paid plans. On the free plan, Supabase recommends exporting your data regularly with the [Supabase CLI `db dump` command](https://supabase.com/docs/reference/cli/supabase-db-dump), or you can export tables as CSV from the **Table Editor**.

---

## API

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/videos` | `{ "url": "...", "quiz_count": 5-20 }` starts analysis (or returns the existing record) |
| `GET` | `/api/videos?search=` | List saved videos, optionally filtered by title |
| `GET` | `/api/videos/{id}` | Full content in both languages |
| `GET` | `/api/videos/{id}/status` | Lightweight progress for polling |
| `DELETE` | `/api/videos/{id}` | Delete a saved video |
| `GET` | `/api/videos/{id}/pdf?language=en\|hinglish` | Download the PDF |
| `GET` | `/api/todos?status=all\|active\|done` | List tasks (open first, then by due date) |
| `POST` | `/api/todos` | `{ "title": "...", "due_date": "2026-12-01" \| null, "video_id": 1 \| null }` |
| `GET` | `/api/todos/{id}` | One task |
| `PATCH` | `/api/todos/{id}` | Change only the fields you send, e.g. `{ "is_done": true }` or `{ "due_date": null }` |
| `DELETE` | `/api/todos/{id}` | Delete a task |
| `POST` | `/api/videos/{id}/quiz-results` | `{ "language": "en", "answers": [0, 2, null, …] }`. The server scores the answers and saves the attempt |
| `GET` | `/api/videos/{id}/quiz-results` | The last 10 attempts for a video |
| `GET` | `/api/me` | The signed-in user's profile and stats |
| `PATCH` | `/api/me` | `{ "full_name": "..." }` |
| `GET` / `PATCH` | `/api/me/preferences` | `{ "theme": "dark", "default_language": "en", "default_quiz_count": 10 }` |
| `GET` | `/api/config` | Public settings for the browser (whether accounts are on, Supabase URL and publishable key) |
| `GET` | `/api/health` | Health check |

With accounts on, every endpoint except `/api/config` and `/api/health` needs an `Authorization: Bearer <access token>` header. Without one the API answers `401`. Another user's video or task is always reported as `404`.

Interactive docs: http://127.0.0.1:8000/docs

---

## Running the tests

The backend has a pytest suite. It uses a temporary database and fake HTTP responses, so it never touches your saved notes or uses API credits.

```powershell
cd vidnotes-ai\backend
.venv\Scripts\activate
python -m pytest
```

The frontend has no unit tests. `npm run build` checks that it compiles.

**Optional: Row Level Security tests.** `tests/test_postgres_rls.py` checks the real database policies: a user can't read, change, delete or link to another user's data, and signed-out visitors get nothing. They need a Postgres database with the Supabase schema. **Never point them at your real project**, because they create and delete test users. Use a local Supabase started with the [Supabase CLI](https://supabase.com/docs/guides/local-development) (requires Docker), apply the SQL file, then:

```powershell
$env:TEST_SUPABASE_DB_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
python -m pytest
```

Without that variable these tests are skipped.

---

## Security notes

- API keys (Gemini, Supadata, Groq) and the database password live only in `backend/.env`. They are never returned by the API or included in frontend code.
- The only Supabase value the browser sees is the **publishable** key, which Supabase designed to be public. No secret or `service_role` key is used anywhere.
- Passwords are never stored by VidNotes: Supabase Auth handles them. The Google client secret is entered only in the Supabase Dashboard.
- Every request is checked against the signed-in user, and in cloud mode Postgres Row Level Security enforces it again at the database level.
- `.env` and the database are in `.gitignore`. **Never commit real keys.** If a key is ever shared publicly, revoke it and create a new one.
- Only YouTube URLs are accepted. The backend extracts the 11-character video ID and never fetches the user's URL, which prevents SSRF.
- Request bodies over 16 KB are rejected. Inputs are validated with Pydantic.
- CORS allows only the origins in `CORS_ORIGINS`.

## Troubleshooting

| Message | Fix |
| --- | --- |
| *Cannot reach the VidNotes server* | The backend is not running on port 8000. |
| *… rejected the API key* | Check the key in `backend/.env`, then restart the backend. |
| *daily Gemini quota … used up* | Wait until tomorrow, add models to `GEMINI_FALLBACK_MODELS`, or enable billing. |
| *Gemini is busy* | Google's servers are overloaded. Try again in a few minutes. |
| *no transcript available* / *No speech was detected* | The video has no captions or speech Supadata can use. With `SUPADATA_TRANSCRIPT_MODE=native`, videos without captions always fail. |
| *Supadata rate or credit limit reached* | Wait a minute, or check your remaining credits in the Supadata dashboard. |
| *Groq's answer was cut off …* | The Groq free tier is too small for this video. Wait for Gemini's quota to reset, or use a paid Groq tier. |
| *daily Groq limit … used up* | Groq's daily token limit is reached. Try again tomorrow. |
| *The Supabase database is missing tables* | Run `supabase/migrations/20261108000000_vidnotes_schema.sql` in the Supabase SQL Editor. |
| Backend can't connect to the database / timeout | Use the **Session pooler** connection string (not "Direct connection"), check the password, and URL-encode special characters. |
| *Your session has expired* | Log in again. |
| *Please confirm your email first* | Open the link in the confirmation email (check spam), or switch off **Confirm email** in Supabase. |
| *Google sign-in is not set up yet* | Enable the Google provider in Supabase (see [Google sign-in](#google-sign-in-optional)). |
| Google says `redirect_uri_mismatch` | The Google client's **Authorized redirect URI** must be exactly `https://<project-ref>.supabase.co/auth/v1/callback`. |
| Reset or confirmation link opens the wrong site | Set the **Site URL** and **Redirect URLs** in Supabase → Authentication → URL Configuration. |
| *This link must be opened in the same browser* | Open password-reset links in the browser where you requested them. |

---

## Deployment

You don't need to deploy to use VidNotes; local mode and cloud mode both work from your own computer. Deploying lets you open it from your phone or any device without running anything locally. Cloud mode (Supabase) is required for this, because hosted servers don't keep local files.

A free-tier-friendly setup:

| Part | Where | Settings |
| --- | --- | --- |
| Database + sign-in | Supabase (already set up above) | Add the deployed frontend address to **Site URL** / **Redirect URLs** (e.g. `https://vidnotes.example.com/**`) |
| Backend (FastAPI) | Any Python host with a free tier, e.g. [Render](https://render.com) web service | Root directory `backend`, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Add all `backend/.env` values as environment variables, and set `CORS_ORIGINS` to the frontend address |
| Frontend (static site) | Netlify, Cloudflare Pages or Vercel | Root `frontend`, build `npm run build`, output `dist`. Set `VITE_API_BASE_URL` to the backend address (see `frontend/.env.example`) |

Notes:

- `frontend/public/_redirects` makes page reloads on routes like `/notes/12` work on Netlify and Cloudflare Pages.
- Free backend hosts usually sleep when idle, so the first request after a break can take up to a minute.
- If Google sign-in is on, add the deployed frontend address to the Google client's **Authorized JavaScript origins**.
- Never upload `backend/.env`. Enter the values in the host's environment settings instead.

