# RAK Ceramics — AI Tile Sales Chatbot

An end-to-end intelligent sales assistant built for RAK Ceramics. This application allows customers to find the perfect tiles using natural language queries (e.g., "show me white polished marble tiles for my living room, 60x60").

The system uses a Retrieval-Augmented Generation (RAG) pipeline powered by ChromaDB and the Google Gemini API, featuring a custom hybrid re-ranking engine to ensure high-accuracy, catalog-exclusive product recommendations without hallucinations.

Try out the Sales Assistant at: https://rak-sales-bot.vercel.app

> [!WARNING]
> The backend is deployed on Render (free tier). Hence, the backend will sleep after 15 minutes of inactivity. So the first response may take longer than usual (approx. 1 minute).

Images of the Sales Assistant:

![image alt](https://github.com/mohith-anand/RAK-Sales-Bot/blob/b0c0cda5bbbf4e1a1943d4e9636989dd19e6ef10/Image%201.png)

![image alt](https://github.com/mohith-anand/RAK-Sales-Bot/blob/b0c0cda5bbbf4e1a1943d4e9636989dd19e6ef10/Image%202.png)

![image alt](https://github.com/mohith-anand/RAK-Sales-Bot/blob/b0c0cda5bbbf4e1a1943d4e9636989dd19e6ef10/Image%203.png)

## 🧠 Key AI Capabilities

### 1. Hybrid RAG Pipeline
Built on a **Retrieval-Augmented Generation (RAG)** architecture, the system uses **ChromaDB** to index the RAK product catalog. It translates natural language into high-dimensional vectors (using `gemini-embedding-2`), allowing users to search by "vibe" and "look" rather than just keywords. A strict **0.70 Cosine Similarity Gate** intercepts irrelevant inputs before they reach the LLM, heavily reducing hallucinations.

### 2. Dual-Layer Intent Classification
To optimize API quota and response latency, the system routes queries through a fast hybrid intent classifier:
- **Fast Heuristics**: Instantly blocks conversational noise, pricing inquiries, and greetings using deterministic caching rules.
- **LLM Routing**: Contextual inquiries are routed to a RAG chain to determine if a vector DB extraction is necessary.

### 3. Expert Re-Ranking Engine
Vector similarity alone isn't enough for sales. Our custom **Re-ranking Logic** applies business-aware weighted scoring to the top 60 search candidates:
- **Material Integrity**: Prevents "wood look" tiles from appearing when searching for "marble."
- **Constraint Satisfaction**: Forces strict compliance with Finish (Matt/Polished), Color, Size, and Suitability (Commercial/Domestic).
- **Diversity Algorithm**: Ensures the top 3 results come from different product series to maximize catalog exposure.

### 4. Dual-Model Architecture
Using **Gemini 2.5 Flash** for production speed, the advisor maintains a 10-message conversational memory handling multi-turn design discussions (e.g., *"Show me those in grey"*). Internally, the Evaluation and System Audit suite uses the rigorous **Gemini 3.0 Flash Preview** model as a benchmark Judge.

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

### **Complete E2E Assessment**
Run the advanced evaluation suite to test Generation, Refusals, and Coherence:
```bash
python scripts/evaluate_e2e.py
```
This script uses **LLM-as-a-Judge** to verify:
- **Faithfulness**: Zero tolerance for hallucinations.
- **Refusal Accuracy**: Proper handling of pricing/competitor queries.
- **Multi-turn Logic**: Consistency across sequential design prompts.

### **Comprehensive System Health Check**
A full 8-layer system audit (`system_health_check.py`) was run against the entire RAG pipeline yielding a **100% Pass Rate (37/37 tests)**:

| Layer | Component | Result |
|---|---|---|
| **Layer 0** | Database Integrity | ✅ 547 properties indexed |
| **Layer 1** | Embedding & Vector Retrieval | ✅ Passing (valid metadata/vectors) |
| **Layer 2** | Similarity Threshold Gate | ✅ Passing (rejects non-ceramics at < 0.70) |
| **Layer 3** | Re-ranking Rules | ✅ Passing (material, surface, color, size) |
| **Layer 4** | Diversity Algorithm | ✅ Passing (results from ≥2 series) |
| **Layer 5** | Intent Classifier | ✅ Passing (blocks rate limits via heuristic layer) |
| **Layer 6** | E2E Pipeline (Search + Generate) | ✅ Passing (accurate context generation) |
| **Layer 7** | Safety & Refusal Guards | ✅ Passing (blocks pricing/competitors) |

To run the full suite:
```bash
python scripts/system_health_check.py
```

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
