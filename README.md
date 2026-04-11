# RAK Ceramics — AI Tile Sales Chatbot

An end-to-end intelligent sales assistant built for RAK Ceramics. This application allows customers to find the perfect tiles using natural language queries (e.g., *"show me white polished marble tiles for my living room, 60x60"*). 

The system uses a **Retrieval-Augmented Generation (RAG)** pipeline powered by **ChromaDB** and the **Google Gemini API**, featuring a custom hybrid re-ranking engine to ensure high-accuracy, catalog-exclusive product recommendations without hallucinations.

---

## 🏗️ Architecture & Tech Stack

### Frontend
- **React 19** & **TypeScript**
- **Vite 6**
- **Tailwind CSS v4**
- **Framer Motion** (Scroll-triggered animations & transitions)

### Backend
- **Python 3.9+** & **FastAPI**
- **ChromaDB** (Local Vector Database)
- **Google Gemini API** (`gemini-embedding-2-preview` & `gemini-2.5-flash`)
- **Pandas** & **OpenPyXL** (Data processing)

---

## 🚀 How to Run Locally

Follow these steps to run the complete system on your personal computer.

### Prerequisites
1. **Python 3.9+** installed
2. **Node.js (v18+)** installed
3. A **Google Gemini API Key** (Get one free from [Google AI Studio](https://aistudio.google.com/))

### 1. Setup Environment Variables
At the root of the project, create a `.env` file and add your Gemini API key:
```env
GEMINI_API_KEY=your_actual_api_key_here
```

### 2. Start the Backend (FastAPI + ChromaDB)

Open a terminal in the project root and run:

```bash
# Navigate to backend
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
.\venv\Scripts\activate
# On Mac/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn main:app --reload --port 8000
```
*The backend API will now be running at `http://localhost:8000`*

### 3. Start the Frontend (React + Vite)

Open a **second** terminal instance in the project root and run:

```bash
# Navigate to frontend
cd frontend

# Install Node dependencies
npm install

# Start the development server
npm run dev
```
*The frontend application will normally run at `http://localhost:3000` or `http://localhost:5173`. Check the terminal output for the exact URL.*

---

## 🧠 System Highlights

### Hybrid Re-Ranking Engine
Instead of relying purely on vector similarity (which can cause hallucinations, like returning wood-look tiles when asking for marble), this system applies **strict penalty-based scoring rules**. It evaluates:
1. **Material Type** (Marble, Concrete, Stone, Wood)
2. **Surface Finish** (Polished vs. Matte)
3. **Color Grouping**
4. **Dimensions & Usage Profile** 

This approach boosts Recommendation Accuracy (Precision@3) from ~83% (Baseline AI) to **96.7%**.

### Conversational Memory
The backend maintains a rolling 10-message conversational context, allowing users to ask complex follow-up queries (e.g., *"What about in grey?"*) without losing track of their previous constraints.

### Result Diversification
An integrated algorithm ensures top results span multiple unique product series, maximizing catalog exposure rather than showing 3 identical tiles from a single collection.

---

## 📝 Evaluation Metrics

A dedicated evaluation script (`backend/scripts/evaluate.py`) tests the engine against 20 complex architectural queries. Our current metrics stand at:
- **Constraint Satisfaction Rate (CSR):** 96.7% Precision@3
- **Mean Reciprocal Rank (MRR):** 0.983
- **Series Diversity:** 86.7% unique series in top results

To run the evaluation suite yourself:
```bash
cd backend
.\venv\Scripts\activate
python scripts/evaluate.py
```
