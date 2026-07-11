# IPO Copilot AI

AI-powered SME IPO Offer Document Preparation and SEBI Compliance Platform.
Built for the SEBI Securities Market TechSprint Hackathon 2026.

## Production Setup Instructions (Windows)

### Prerequisites
1. Python 3.10+
2. Node.js 18+
3. Git

### Backend Setup
1. Open PowerShell and navigate to the `backend` directory.
2. Create and activate a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Set up the `.env` file (provide your API keys for the LLM).
5. Start the production server using Uvicorn:
   ```powershell
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
   ```

### Frontend Setup
1. Open PowerShell and navigate to the `frontend` directory.
2. Install dependencies:
   ```powershell
   npm install
   ```
3. Build the production bundle:
   ```powershell
   npm run build
   ```
4. Preview or serve the production build:
   ```powershell
   npm run preview
   ```

### Security & Compliance
- The application automatically isolates workspace data.
- The `UPLOAD_DIR` and `CHROMA_PERSIST_DIR` are created at runtime. Ensure the service account running the backend has adequate file read/write permissions for these directories.
- All AI responses are traceable through the Evidence Rail.

### Architecture Overview
- **Backend:** FastAPI + SQLAlchemy + LangChain + ChromaDB.
- **Frontend:** React + TypeScript + TanStack Query + Zustand.
