# Deployment Guide: IPO Copilot AI

This document provides step-by-step instructions for deploying the IPO Copilot AI platform to production for the SEBI Securities Market TechSprint 2026.

We use **Railway** for the backend (FastAPI, SQLite, ChromaDB) and **Vercel** for the frontend (React, Vite).

---

## Part 1: Backend Deployment (Railway)

We use Railway.app because it provides persistent storage for our SQLite database and ChromaDB vectors.

1. **Create a Railway Account**
   - Go to [Railway.app](https://railway.app/) and sign in with GitHub.

2. **Initialize the Project**
   - Click **New Project** -> **Deploy from GitHub repo**.
   - Select the `SEBI HACKATHON` repository.
   - Railway will automatically detect the Python environment and read the `Procfile` / `railway.json` we created.

3. **Configure Persistent Volumes**
   - This is crucial! Without volumes, our SQLite DB and Chroma vectors will be wiped on every redeploy.
   - Go to your Railway service settings -> **Volumes**.
   - Add a volume mounted at `/app/data` (or the equivalent directory depending on your `DATABASE_URL` and `CHROMA_PERSIST_DIR` paths).

4. **Environment Variables**
   - In the Railway dashboard, go to the **Variables** tab. Add the following:
     ```env
     DATABASE_URL=sqlite+aiosqlite:////app/data/ipo_copilot.db
     SECRET_KEY=<generate_a_secure_random_string>
     GOOGLE_API_KEY=<your_google_gemini_api_key>
     GROQ_API_KEY=<your_groq_api_key>
     LLM_PROVIDER=groq
     CHROMA_PERSIST_DIR=/app/data/chroma_db
     UPLOAD_DIR=/app/data/uploads
     ALLOWED_ORIGINS=https://ipo-copilot.vercel.app
     ```

5. **Deploy**
   - Railway will trigger a build using Nixpacks (as defined in `railway.json`). 
   - Once deployed, grab the public Railway URL (e.g., `https://backend-production.up.railway.app`).

---

## Part 2: Frontend Deployment (Vercel)

Vercel provides blazing-fast edge delivery for our React SPA.

1. **Create a Vercel Account**
   - Go to [Vercel.com](https://vercel.com/) and sign in with GitHub.

2. **Import Project**
   - Click **Add New Project**.
   - Select the `SEBI HACKATHON` repository.
   - **Important**: In the "Framework Preset" dropdown, select **Vite**.
   - **Important**: In the "Root Directory" section, click Edit and select `frontend/`.

3. **Environment Variables**
   - In the deployment configuration, expand "Environment Variables". Add:
     ```env
     VITE_API_BASE_URL=https://<your_railway_app_url>.up.railway.app/api/v1
     ```

4. **Deploy**
   - Click **Deploy**. Vercel will install dependencies, build the React app, and deploy it to a live `.vercel.app` URL.

---

## Verification

1. **Health Check**: Open `<your_railway_app_url>/health` in your browser. You should see `{"status": "healthy", "version": "1.0.0"}`.
2. **End-to-End**: Open your Vercel frontend URL, register a new account, and create a workspace to ensure the database and API are fully connected.

Good luck with the Hackathon pitch!
