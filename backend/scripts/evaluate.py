"""
RAK Ceramics - Tile Recommendation System Evaluation
=====================================================
Metrics computed:
  1. Constraint Satisfaction Rate (CSR)  — % of results satisfying query constraints
  2. Re-ranking Lift                     — CSR Before vs After re-ranking
  3. Mean Reciprocal Rank (MRR)          — How high the first correct result ranks
  4. Mean Average Precision @ 3 (MAP@3) — Ranking quality across all queries
  5. Series Diversity Score              — Unique series in top results

Run from backend/ directory:
    python scripts/evaluate.py
"""

import os
import sys
import json
from pathlib import Path

# --- Path Setup ---
BASE_DIR = Path(__file__).resolve().parent          # backend/scripts/
BACKEND_DIR = BASE_DIR.parent                        # backend/
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

import chromadb
import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY not set in backend/.env")

genai.configure(api_key=api_key)

CHROMA_PATH  = str(BACKEND_DIR / "data" / "vector_db")
EMBED_MODEL  = "models/gemini-embedding-2-preview"
N_RESULTS    = 3       # Top-K to evaluate
N_CANDIDATES = 60      # Pool size (same as production)

client     = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection("rak_tiles_products")

print(f"✅ Connected — {collection.count()} products in DB\n")

# ─────────────────────────────────────────────────────────
# TEST SUITE
# Each entry: query + the constraints that MUST be satisfied
# Constraints are checked against tile metadata fields.
# ─────────────────────────────────────────────────────────
TEST_QUERIES = [
    # Material tests
    {
        "query": "marble tiles for living room",
        "must": {"category": "marble"},
        "label": "Material: Marble"
    },
    {
        "query": "concrete look tiles for kitchen",
        "must": {"category": "concrete"},
        "label": "Material: Concrete"
    },
    {
        "query": "wood effect tiles for bedroom",
        "must": {"category": "wood"},
        "label": "Material: Wood"
    },
    {
        "query": "stone finish tiles for bathroom",
        "must": {"category": "stone"},
        "label": "Material: Stone"
    },

    # Surface finish tests
    {
        "query": "polished floor tiles",
        "must": {"surface": "polished"},
        "label": "Finish: Polished"
    },
    {
        "query": "matte tiles for bathroom wall",
        "must": {"surface": "matt"},
        "label": "Finish: Matte"
    },

    # Color tests
    {
        "query": "white tiles for bathroom",
        "must_color_group": ["white", "active white", "supreme white", "ivory", "cream", "calacatta"],
        "label": "Color: White"
    },
    {
        "query": "grey floor tiles for living room",
        "must_color_group": ["grey", "gray", "silver grey", "ash", "warm grey", "platinum"],
        "label": "Color: Grey"
    },
    {
        "query": "black tiles for feature wall",
        "must_color_group": ["black", "anthracite", "charcoal", "graphite", "dark"],
        "label": "Color: Black/Dark"
    },
    {
        "query": "beige tiles for bedroom floor",
        "must_color_group": ["beige", "taupe", "sand", "brown"],
        "label": "Color: Beige/Warm"
    },

    # Combined constraint tests (hardest)
    {
        "query": "white polished marble tiles 60x60",
        "must": {"category": "marble", "surface": "polished"},
        "must_color_group": ["white", "active white", "supreme white", "ivory", "calacatta"],
        "label": "Combined: White Polished Marble 60x60"
    },
    {
        "query": "grey matte concrete tiles for living room",
        "must": {"category": "concrete", "surface": "matt"},
        "must_color_group": ["grey", "gray", "silver grey", "ash"],
        "label": "Combined: Grey Matte Concrete"
    },
    {
        "query": "dark polished marble tiles",
        "must": {"category": "marble", "surface": "polished"},
        "must_color_group": ["black", "anthracite", "charcoal", "dark"],
        "label": "Combined: Dark Polished Marble"
    },

    # Usage suitability tests
    {
        "query": "heavy commercial tiles for office lobby",
        "must_suitable": "commercial",
        "label": "Usage: Commercial"
    },
    {
        "query": "outdoor patio tiles slip resistant",
        "must": {"application": "outdoor"},
        "label": "Usage: Outdoor"
    },

    # Size tests
    {
        "query": "large format 60x60 tiles",
        "must_size": "60x60",
        "label": "Size: 60x60"
    },
    {
        "query": "30x60 wall tiles for bathroom",
        "must_size": "30x60",
        "label": "Size: 30x60"
    },

    # Natural language / conversational
    {
        "query": "something luxurious and elegant for master bedroom",
        "must": {"category": "marble"},
        "label": "NL: Luxurious / Elegant"
    },
    {
        "query": "minimalist modern look for open plan living",
        "must": {},
        "label": "NL: Minimalist Modern (no hard constraint)"
    },
    {
        "query": "tiles that look like natural stone for garden",
        "must": {"category": "stone"},
        "label": "NL: Natural Stone Garden"
    },
]


# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

def embed_query(query: str) -> list:
    result = genai.embed_content(
        model=EMBED_MODEL,
        content=f"task: retrieval_query | {query}",
        task_type="retrieval_query"
    )
    return result["embedding"] if "embedding" in result else result["embeddings"][0]


def fetch_candidates(query_embedding: list) -> list:
    """Fetch 60 raw candidates from ChromaDB."""
    raw = collection.query(query_embeddings=[query_embedding], n_results=N_CANDIDATES)
    candidates = []
    for i in range(len(raw["ids"][0])):
        meta  = raw["metadatas"][0][i]
        dist  = raw["distances"][0][i]
        candidates.append({
            "sku":          raw["ids"][0][i],
            "category":     meta.get("category", "").lower(),
            "series_name":  meta.get("series_name", "").lower(),
            "surface":      meta.get("surface", "").lower(),
            "color":        meta.get("color", "").lower(),
            "size_cm":      meta.get("size_cm", "").lower().replace(" ", ""),
            "suitable_for": meta.get("suitable_for", "").lower(),
            "application":  meta.get("application", "").lower(),
            "base_score":   round(1 - dist, 4),
        })
    return candidates


def is_relevant(tile: dict, test: dict) -> bool:
    """
    Returns True if a tile satisfies ALL constraints in the test case.
    All tile field values are lowercased before comparison so this works
    regardless of whether search_tiles() or fetch_candidates() returned them.
    """
    # Hard field constraints
    for field, keyword in test.get("must", {}).items():
        tile_val = tile.get(field, "").lower()
        if keyword.lower() not in tile_val:
            return False

    # Color group constraint
    color_group = test.get("must_color_group", [])
    if color_group:
        tile_color = tile.get("color", "").lower()
        if not any(c.lower() in tile_color for c in color_group):
            return False

    # Suitability constraint
    must_suitable = test.get("must_suitable", "")
    if must_suitable:
        tile_suitable = tile.get("suitable_for", "").lower()
        if must_suitable.lower() not in tile_suitable:
            return False

    # Size constraint
    must_size = test.get("must_size", "")
    if must_size:
        tile_size = tile.get("size_cm", "").lower().replace(" ", "")
        if must_size.lower() not in tile_size:
            return False

    return True


def precision_at_k(results: list, test: dict, k: int = 3) -> float:
    hits = sum(1 for r in results[:k] if is_relevant(r, test))
    return hits / k


def reciprocal_rank(results: list, test: dict) -> float:
    for rank, tile in enumerate(results, start=1):
        if is_relevant(tile, test):
            return 1.0 / rank
    return 0.0


def average_precision_at_k(results: list, test: dict, k: int = 3) -> float:
    hits, score = 0, 0.0
    for i, tile in enumerate(results[:k], start=1):
        if is_relevant(tile, test):
            hits += 1
            score += hits / i
    return score / k if k > 0 else 0.0


def diversity_score(results: list, k: int = 3) -> float:
    series = [r.get("series_name", "") for r in results[:k]]
    unique = len(set(s for s in series if s))
    return unique / k if k > 0 else 0.0


# ─────────────────────────────────────────────────────────
# IMPORT RE-RANKER  (production code, unchanged)
# ─────────────────────────────────────────────────────────
from run.services.product_search_service import search_tiles


# ─────────────────────────────────────────────────────────
# MAIN EVALUATION LOOP
# ─────────────────────────────────────────────────────────

results_log = []

base_precisions, rerank_precisions = [], []
base_mrrs,       rerank_mrrs       = [], []
base_maps,       rerank_maps       = [], []
diversity_scores = []

print("=" * 65)
print(f"  RAK CERAMICS — EVALUATION SUITE  ({len(TEST_QUERIES)} queries, @K={N_RESULTS})")
print("=" * 65)

for i, test in enumerate(TEST_QUERIES, start=1):
    query = test["query"]
    label = test["label"]

    print(f"\n[{i:02d}/{len(TEST_QUERIES)}] {label}")
    print(f"       Query: \"{query}\"")

    # --- Embed once, share between base & re-ranked ---
    embedding = embed_query(query)
    candidates = fetch_candidates(embedding)

    # --- BASE: rank purely by cosine similarity ---
    base_top = sorted(candidates, key=lambda x: x["base_score"], reverse=True)[:N_RESULTS]

    # --- RE-RANKED: use production search_tiles ---
    reranked_top = search_tiles(query, n_results=N_RESULTS)

    # --- Compute metrics ---
    bp  = precision_at_k(base_top, test, N_RESULTS)
    rp  = precision_at_k(reranked_top, test, N_RESULTS)
    bm  = reciprocal_rank(base_top, test)
    rm  = reciprocal_rank(reranked_top, test)
    bap = average_precision_at_k(base_top, test, N_RESULTS)
    rap = average_precision_at_k(reranked_top, test, N_RESULTS)
    div = diversity_score(reranked_top, N_RESULTS)

    base_precisions.append(bp)
    rerank_precisions.append(rp)
    base_mrrs.append(bm)
    rerank_mrrs.append(rm)
    base_maps.append(bap)
    rerank_maps.append(rap)
    diversity_scores.append(div)

    lift = rp - bp
    lift_str = f"+{lift:.2f}" if lift >= 0 else f"{lift:.2f}"

    print(f"       Precision@{N_RESULTS}: Base={bp:.2f}  →  Re-ranked={rp:.2f}  (Lift {lift_str})")
    print(f"       MRR:          Base={bm:.2f}  →  Re-ranked={rm:.2f}")
    print(f"       Diversity:    {div:.2f}  ({int(div * N_RESULTS)}/{N_RESULTS} unique series)")

    # Log top results
    log_entry = {
        "query": query,
        "label": label,
        "base_top3":     [{"sku": r["sku"], "series": r["series_name"], "category": r["category"],
                           "surface": r["surface"], "color": r["color"], "base_score": r["base_score"]}
                          for r in base_top],
        "reranked_top3": [{"sku": r["sku"], "series": r["series_name"], "category": r["category"],
                           "surface": r["surface"], "color": r["color"],
                           "base_score": r.get("base_score", 0), "final_score": r.get("final_score", 0)}
                          for r in reranked_top],
        "metrics": {
            "base_precision": bp, "rerank_precision": rp,
            "base_mrr": bm,       "rerank_mrr": rm,
            "base_map": bap,      "rerank_map": rap,
            "diversity": div
        }
    }
    results_log.append(log_entry)


# ─────────────────────────────────────────────────────────
# SUMMARY REPORT
# ─────────────────────────────────────────────────────────

def avg(lst): return sum(lst) / len(lst) if lst else 0.0

mean_bp  = avg(base_precisions)
mean_rp  = avg(rerank_precisions)
mean_bm  = avg(base_mrrs)
mean_rm  = avg(rerank_mrrs)
mean_bap = avg(base_maps)
mean_rap = avg(rerank_maps)
mean_div = avg(diversity_scores)
lift_p   = mean_rp - mean_bp
lift_m   = mean_rm - mean_bm

print("\n")
print("=" * 65)
print("  EVALUATION SUMMARY")
print("=" * 65)
print(f"  Total queries evaluated : {len(TEST_QUERIES)}")
print(f"  Top-K (N_RESULTS)       : {N_RESULTS}")
print(f"  Collection size         : {collection.count()} products")
print()
print(f"  {'Metric':<35} {'Base':>8}  {'Re-ranked':>9}  {'Lift':>7}")
print(f"  {'-'*60}")
print(f"  {'Precision@' + str(N_RESULTS) + ' (CSR)':<35} {mean_bp:>8.1%}  {mean_rp:>9.1%}  {lift_p:>+7.1%}")
print(f"  {'Mean Reciprocal Rank (MRR)':<35} {mean_bm:>8.3f}  {mean_rm:>9.3f}  {lift_m:>+7.3f}")
print(f"  {'Mean Average Precision (MAP@' + str(N_RESULTS) + ')':<35} {mean_bap:>8.3f}  {mean_rap:>9.3f}  {avg(rerank_maps)-avg(base_maps):>+7.3f}")
print(f"  {'Series Diversity Score':<35} {'—':>8}  {mean_div:>9.1%}  {'—':>7}")
print("=" * 65)

# Save full results to JSON
OUTPUT_PATH = BASE_DIR / "eval_results.json"
with open(OUTPUT_PATH, "w") as f:
    json.dump({
        "summary": {
            "total_queries": len(TEST_QUERIES),
            "k": N_RESULTS,
            "collection_size": collection.count(),
            "base_precision":  round(mean_bp, 4),
            "rerank_precision": round(mean_rp, 4),
            "precision_lift":  round(lift_p, 4),
            "base_mrr":        round(mean_bm, 4),
            "rerank_mrr":      round(mean_rm, 4),
            "mrr_lift":        round(lift_m, 4),
            "base_map":        round(mean_bap, 4),
            "rerank_map":      round(mean_rap, 4),
            "diversity_score": round(mean_div, 4),
        },
        "per_query": results_log
    }, f, indent=2)

print(f"\n  📄 Full results saved → scripts/eval_results.json")
print()

# Resume-ready summary
print("─" * 65)
print("  RESUME-READY NUMBERS (after running this):")
print("─" * 65)
print(f"  • Constraint Satisfaction Rate  : {mean_rp:.0%} Precision@{N_RESULTS} (re-ranked)")
print(f"  • Re-ranking Lift over baseline : {lift_p:+.0%} Precision@{N_RESULTS} improvement")
print(f"  • Mean Reciprocal Rank (MRR)    : {mean_rm:.3f}")
print(f"  • Series Diversity              : {mean_div:.0%} unique series in top results")
print("─" * 65)
