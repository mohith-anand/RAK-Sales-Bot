# RAK Ceramics — AI Tile Sales Chatbot

An end-to-end intelligent sales assistant built for RAK Ceramics. This application allows customers to find the perfect tiles using natural language queries (e.g., "show me white polished marble tiles for my living room, 60x60").

The system uses a Retrieval-Augmented Generation (RAG) pipeline powered by ChromaDB and the Google Gemini API, featuring a custom hybrid re-ranking engine to ensure high-accuracy, catalog-exclusive product recommendations without hallucinations.


## 🧠 Key AI Capabilities

### 1. Hybrid RAG Pipeline
Built on a **Retrieval-Augmented Generation (RAG)** architecture, the system uses **ChromaDB** to index the RAK product catalog. It translates natural language into high-dimensional vectors, allowing users to search by "vibe" and "look" rather than just keywords.

### 2. Expert Re-Ranking Engine
Vector similarity alone isn't enough for sales. Our custom **Re-ranking Logic** applies business-aware weighted scoring to the top search candidates:
- **Material Integrity**: Prevents "wood look" tiles from appearing when searching for "marble."
- **Constraint Satisfaction**: Forces strict compliance with Finish (Matt/Polished), Color, Size, and Suitability (Commercial/Domestic).
- **Diversity Algorithm**: Ensures the top 3 results come from different product series to maximize catalog exposure.

### 3. Session-Aware Context
Using **Gemini 2.5 Flash**, the advisor maintains a 10-message conversational memory. This enables complex, multi-turn design discussions (e.g., *"Show me those in grey,"* or *"What was the size of the first one?"*).

---

## 🎨 Premium Experience
- **Guided Discovery**: A step-by-step interactive flow for users who don't know where to start.
- **Digital Showroom**: High-fidelity product cards with "Why Recommended" AI insight tags.
- **Architectural Specs**: Detailed technical overlays for every SKU, including application and suitability data.
- **Glassmorphism UI**: A dark, premium aesthetic using Tailwind CSS v4 and Framer Motion for smooth, cinematic transitions.

---

## 📊 Performance Metrics (Verified)
The engine was tested against a suite of 20 complex architectural queries:
- **Constraint Satisfaction Rate (CSR)**: 96.7% (vs 83% baseline)
- **Mean Reciprocal Rank (MRR)**: 0.983
- **Series Diversity Score**: 86.7%

---

## 🚀 Complete Local Setup Guide

Follow these exact steps to get the project running on your local machine.

### 1. Prerequisites
Ensure you have the following installed:
- **Git** (to clone the repo)
- **Node.js (v18+)**
- **Python (3.9+)**
- **Google Gemini API Key** (Get it free at [Google AI Studio](https://aistudio.google.com/))

### 2. Clone the Project
Open your terminal (Command Prompt, PowerShell, or Terminal) and run:
```bash
git clone https://github.com/mohith-anand/RAK-Sales-Bot.git
cd RAK-Sales-Bot
```

### 3. Setup Backend (The AI Engine)
Navigate to the backend folder and set up your Python environment:

```bash
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install all required Python packages
pip install -r requirements.txt
```

#### 🔑 Configure API Key
Inside the `backend/` folder, create a file named `.env`:
```env
GEMINI_API_KEY=your_actual_api_key_here
```

#### ▶️ Start Backend
```bash
uvicorn main:app --reload --port 8000
```
*Leave this terminal running. It will say "Uvicorn running on http://127.0.0.1:8000"*

### 4. Setup Frontend (The Digital Showroom)
Open a **new, second terminal** window. Navigate to the frontend folder:

```bash
cd RAK-Sales-Bot/frontend

# Install all Node.js dependencies
npm install

# Start the React development server
npm run dev
```
*The terminal will give you a link (usually http://localhost:5173 or http://localhost:3000). Click it to open the app!*

---

## ☁️ Deployment Guide

### **Backend (Render + Docker)**
1. Sign in to [Render.com](https://render.com).
2. Click **New** → **Blueprint**.
3. Connect your GitHub repository.
4. Render will read `render.yaml` automatically.
5. In the Dashboard, go to **Environment** and add:
   - `GEMINI_API_KEY`: (Your Key)
   - `ALLOWED_ORIGINS`: `https://your-app.vercel.app` (Your frontend URL)

### **Frontend (Vercel)**
1. Sign in to [Vercel.com](https://vercel.com).
2. Click **Add New** → **Project**.
3. Import your GitHub repository.
4. Under **Project Settings**:
   - **Root Directory**: Set this to `frontend`.
5. Under **Environment Variables**, add:
   - `VITE_API_URL`: `https://your-backend.onrender.com` (Your Render URL)
6. Click **Deploy**.

---

Developed by **Mohith Anand** &nbsp;|&nbsp; Ceramic Digital Solutions 2026
