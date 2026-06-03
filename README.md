# Steelera

Mobile-first Micro-SaaS PWA for structural steel and light-gauge steel design.

## Prerequisites

- Node.js 20+
- Python 3.11+
- OpenAI API key

## Setup

### 1. Environment

Copy `.env.example` to `.env`, `frontend/.env.local`, and `backend/.env`. Set `OPENAI_API_KEY` in `backend/.env`.

### 2. Install

Backend: `cd backend`, `python -m venv .venv`, `.venv\Scripts\pip install -r requirements.txt`

Frontend: `cd frontend`, `npm install`

Root (optional): `npm install` for `npm run dev` to run both.

### 3. Run

Ask Cursor to **start the app**, or from repo root: `npm run dev`

- Frontend: http://localhost:3000
- Backend: http://127.0.0.1:8000

## API

- `GET http://127.0.0.1:8000/health`
- `POST http://127.0.0.1:8000/api/chat`

## Stack

- **Frontend:** Next.js (App Router), TypeScript, Tailwind, shadcn/ui, React Three Fiber, Serwist PWA
- **Backend:** FastAPI, OpenAI GPT-4o-mini (function calling), Python geometry engine
