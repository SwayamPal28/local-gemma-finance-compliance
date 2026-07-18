# Local-Gemma-Based-Financial-Compliance-and-Risk-Triage

This is a full-stack web application with a React (Vite) frontend and a Python (FastAPI) backend.

## Project Structure

- `frontend/`: The React application using Vite.
- `backend/`: The FastAPI backend application.

## Prerequisites

- Node.js (for frontend)
- Python 3.9+ (for backend)

## How to Run

### Backend

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. (Optional but recommended) Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```
   The backend will run on `http://127.0.0.1:8000`

### Frontend

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies (if you haven't already):
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   The frontend will typically run on `http://localhost:5173`
