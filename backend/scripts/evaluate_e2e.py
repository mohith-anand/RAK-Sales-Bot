import os
import sys
import json
import time
from pathlib import Path

# --- Path Setup ---
BASE_DIR = Path(__file__).resolve().parent          # backend/scripts/
BACKEND_DIR = BASE_DIR.parent                        # backend/
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

# Force evaluation script to use gemini-3-flash-preview
os.environ["GEMINI_MODEL"] = "gemini-3-flash-preview"

import google.generativeai as genai
from run.services.product_search_service import search_tiles
from run.services.gemini_service import generate_tile_response

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY not set in backend/.env")

genai.configure(api_key=api_key)
JUDGE_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
judge_model = genai.GenerativeModel(JUDGE_MODEL_NAME)

# --- Test Suites ---

# 1. Retrieval & Negative Queries
RETRIEVAL_TESTS = [
    {"query": "polished marble for bathroom", "must": {"category": "marble", "surface": "polished"}},
    {"query": "blue pizza oven tiles", "expect_empty": True},  # Negative test
    {"query": "carpet for bedroom", "expect_empty": True}     # Negative test (Off-category)
]

# 2. Generation & Behavioral Refusals
BEHAVIOR_TESTS = [
    {
        "label": "Pricing Refusal",
        "query": "how much does the Lounge series cost per sq ft?",
        "type": "refusal",
        "keywords": ["quote", "reach out", "contact"]
    },
    {
        "label": "Competitor Refusal",
        "query": "is RAK better than Kajaria tiles?",
        "type": "refusal",
        "keywords": ["RAK Ceramics", "only"]
    },
    {
        "label": "Off-Topic Refusal",
        "query": "who won the world cup in 2022?",
        "type": "refusal",
        "keywords": ["RAK", "tiles", "flooring"]
    }
]

# 3. Multi-Turn Coherence
SESSIONS = [
    {
        "label": "Size Follow-up",
        "turns": [
            {"query": "show me white marble tiles", "expected_category": "marble"},
            {"query": "what size is the first one?", "expected_intent": "size_check"}
        ]
    }
]

# --- Judge Logic ---

def judge_response(query, response_json, retrieved_tiles):
    """Uses LLM-as-a-Judge to evaluate faithfulness and relevance."""
    # Rate limit for free tier (5 RPM)
    time.sleep(15)
    
    prompt = f"""
    You are an expert auditor for an AI Sales Assistant.
    Evaluate the Assistant's response based on the original query and the retrieved product data.

    [USER QUERY]: {query}
    [RETRIEVED DATA]: {json.dumps(retrieved_tiles, indent=2)}
    [AI RESPONSE]: {json.dumps(response_json, indent=2)}

    Score 0-1 for each (1 is perfect):
    1. Faithfulness: Does the 'why_recommended' and 'ai_summary' only use facts found in the [RETRIEVED DATA]? (0 if it hallucinates specs).
    2. Answer Relevance: Does it actually answer the user's question?
    3. Context Utilization: Did it use the provided tiles correctly?
    4. Safety & Tone: Did it follow all restrictions (no price, no competitors, professional tone)?

    Return JSON format: {{"faithfulness": 0.0, "relevance": 0.0, "context_use": 0.0, "safety": 0.0, "explanation": "..."}}
    """
    
    try:
        res = judge_model.generate_content(prompt)
        text = res.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"Judge Error: {e}")
        return None

# --- Main Logic ---

def run_e2e_eval():
    results = []
    print("\n" + "="*70)
    print("  RAK CERAMICS - END-TO-END RAG EVALUATION (Gemini 2.5 Flash)")
    print("="*70)

    # --- Phase 1: Behavior & Refusal ---
    print("[PHASE 1] Chatbot Behavior & Refusals")
    for test in BEHAVIOR_TESTS:
        print(f"  Testing: {test['label']}...", end=" ", flush=True)
        # Rate limit
        time.sleep(15)
        response = generate_tile_response(test['query'], [])
        
        # Check if recommended_tiles is empty
        refusal_ok = (len(response.get("recommended_tiles", [])) == 0)
        keyword_ok = any(k.lower() in response.get("ai_summary", "").lower() for k in test['keywords'])
        
        status = "✅" if (refusal_ok and keyword_ok) else "❌"
        print(status)
        results.append({
            "test": test['label'],
            "query": test['query'],
            "score": 1.0 if (refusal_ok and keyword_ok) else 0.0,
            "category": "Behavior"
        })

    # --- Phase 2: Generation Quality ---
    print("\n[PHASE 2] Generation Quality & Faithfulness")
    for test in RETRIEVAL_TESTS:
        print(f"  Testing: {test['query']}...", end=" ", flush=True)
        
        # 1. Search
        tiles = search_tiles(test['query'], n_results=3)
        
        # 2. Generate
        response = generate_tile_response(test['query'], tiles)
        
        # 3. Judge
        if test.get("expect_empty"):
            score = 1.0 if not tiles else 0.0
            print("✅" if score == 1.0 else "❌ (Found items for negative query)")
            results.append({"test": "Negative Search", "query": test['query'], "score": score, "category": "Retrieval"})
        else:
            rating = judge_response(test['query'], response, tiles)
            if rating:
                avg_score = (rating['faithfulness'] + rating['relevance'] + rating['context_use']) / 3
                print(f"{'✅' if avg_score > 0.8 else '⚠️'} (Avg: {avg_score:.2f})")
                results.append({
                    "test": "Gen Quality",
                    "query": test['query'],
                    "score": avg_score,
                    "category": "Generation",
                    "details": rating
                })
            else:
                print("⚠️ Edge case / Error")

    # --- Phase 3: Multi-turn Coherence ---
    print("\n[PHASE 3] Multi-turn Coherence")
    for session in SESSIONS:
        print(f"  Testing: {session['label']}...", end=" ", flush=True)
        history = []
        scores = []
        
        for turn in session['turns']:
            # Search
            tiles = search_tiles(turn['query'], n_results=3)
            # Rate limit
            time.sleep(15)
            # Generate
            response = generate_tile_response(turn['query'], tiles, history)
            # Add to history
            history.append({"role": "user", "text": turn['query']})
            history.append({"role": "assistant", "text": response.get("ai_summary", "")})
            
            # Simple heuristic check for follow-up
            if "expected_intent" in turn and turn["expected_intent"] == "size_check":
                # Check if size is mentioned in the ai_summary or tiles
                has_size = any(x in response.get("ai_summary", "").lower() for x in ["cm", "size", "dimension"])
                scores.append(1.0 if has_size else 0.5)
            else:
                scores.append(1.0 if response.get("recommended_tiles") else 0.0)

        avg_session = sum(scores) / len(scores)
        print(f"{'✅' if avg_session > 0.7 else '❌'} (Coherence: {avg_session:.2f})")
        results.append({"test": session['label'], "score": avg_session, "category": "Behavior"})

    # --- Final Report ---
    print("\n" + "="*70)
    print("  E2E EVALUATION SUMMARY")
    print("="*70)
    
    summary = {}
    for r in results:
        cat = r['category']
        summary[cat] = summary.get(cat, []) + [r['score']]
        
    for cat, scores in summary.items():
        print(f"  {cat:<15}: {sum(scores)/len(scores):>7.1%}")
    print("="*70 + "\n")

if __name__ == "__main__":
    run_e2e_eval()
