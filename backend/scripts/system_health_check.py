"""
RAK Ceramics - Full System Health Check
========================================
Tests every layer of the RAG pipeline in order:
  Layer 0: Database integrity
  Layer 1: Embedding & Vector Retrieval
  Layer 2: Similarity Threshold Gate
  Layer 3: Re-ranking Rules (material, surface, color, size, usage)
  Layer 4: Diversity Algorithm
  Layer 5: Intent Classifier
  Layer 6: End-to-End API Pipeline (search → generate)
  Layer 7: Safety & Refusal Guards
"""

import sys
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Force health check script to use gemini-3-flash-preview
os.environ["GEMINI_MODEL"] = "gemini-3-flash-preview"

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import google.generativeai as genai
from run.services.product_search_service import search_tiles, collection, MIN_SIMILARITY_THRESHOLD
from run.services.gemini_service import requires_product_search, generate_tile_response

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
results_log = []

def check(label, passed, detail=""):
    status = PASS if passed else FAIL
    icon = "+" if passed else "!"
    msg = f"  [{icon}] {label}"
    if detail:
        msg += f"  ({detail})"
    print(msg)
    results_log.append({"label": label, "status": status, "detail": detail})
    return passed


# ─── LAYER 0: Database Integrity ─────────────────────────────────────────────
def layer0_database():
    print("\n[Layer 0] Database Integrity")
    count = collection.count()
    check("Collection exists and is populated", count > 0, f"{count} products")
    check("Product count is 500+", count >= 500, f"{count} products in DB")


# ─── LAYER 1: Embedding & Retrieval ──────────────────────────────────────────
def layer1_retrieval():
    print("\n[Layer 1] Embedding & Vector Retrieval")
    results = search_tiles("white marble polished tiles", n_results=5)
    check("Returns results for a clear tile query", len(results) > 0,
          f"{len(results)} tiles returned")
    check("Results contain required metadata keys", all(
        "series_name" in r and "color" in r and "surface" in r and "sku" in r
        for r in results
    ))
    check("Base similarity scores are between 0 and 1", all(
        0.0 <= r["base_score"] <= 1.0 for r in results
    ))


# ─── LAYER 2: Threshold Gate ──────────────────────────────────────────────────
def layer2_threshold():
    print(f"\n[Layer 2] Similarity Threshold Gate (threshold={MIN_SIMILARITY_THRESHOLD})")
    negative_cases = [
        "carpet for bedroom",
        "sofa for living room",
        "blue pizza oven tiles",
        "who won the world cup",
    ]
    for q in negative_cases:
        r = search_tiles(q, n_results=3)
        check(f"Rejected: '{q}'", len(r) == 0, f"returned {len(r)} results")


# ─── LAYER 3: Re-ranking Rules ────────────────────────────────────────────────
def layer3_reranking():
    print("\n[Layer 3] Re-ranking Rules")

    # 3a. Material integrity
    marble = search_tiles("marble tiles for living room", n_results=3)
    check("Material Rule — marble results contain 'marble' in category",
          all("marble" in r["category"].lower() for r in marble),
          f"Categories: {[r['category'] for r in marble]}")

    concrete = search_tiles("concrete look tiles", n_results=3)
    check("Material Rule — concrete results contain 'concrete' in category",
          all("concrete" in r["category"].lower() for r in concrete),
          f"Categories: {[r['category'] for r in concrete]}")

    # 3b. Surface finish
    polished = search_tiles("polished floor tiles", n_results=3)
    check("Surface Rule — polished query returns polished tiles",
          all("polished" in r["surface"].lower() for r in polished),
          f"Surfaces: {[r['surface'] for r in polished]}")

    matt = search_tiles("matte tiles for bathroom wall", n_results=3)
    check("Surface Rule — matt query returns matt tiles",
          all("matt" in r["surface"].lower() for r in matt),
          f"Surfaces: {[r['surface'] for r in matt]}")

    # 3c. Cross-finish penalty (polished query should NOT return matt tiles)
    check("Surface Penalty — polished query does NOT return matt tiles",
          not any("matt" in r["surface"].lower() for r in polished))

    # 3d. Color grouping
    white = search_tiles("white tiles for bathroom", n_results=3)
    WHITE_COLORS = ["white", "ivory", "cream", "calacatta", "bone", "active"]
    check("Color Rule — white query returns white-family tiles",
          all(any(c in r["color"].lower() for c in WHITE_COLORS) for r in white),
          f"Colors: {[r['color'] for r in white]}")

    grey = search_tiles("grey floor tiles", n_results=3)
    GREY_COLORS = ["grey", "gray", "ash", "silver", "warm grey", "platinum"]
    check("Color Rule — grey query returns grey-family tiles",
          all(any(c in r["color"].lower() for c in GREY_COLORS) for r in grey),
          f"Colors: {[r['color'] for r in grey]}")

    # 3e. Size match
    size_results = search_tiles("large format 60x60 floor tiles", n_results=3)
    check("Size Rule — 60x60 query returns 60x60 tiles",
          any("60x60" in r["size_cm"].replace(" ", "") for r in size_results),
          f"Sizes: {[r['size_cm'] for r in size_results]}")

    # 3f. Usage / suitability
    commercial = search_tiles("heavy commercial tiles for office lobby", n_results=3)
    check("Usage Rule — commercial query returns commercially-suitable tiles",
          any("commercial" in r["suitable_for"].lower() for r in commercial),
          f"Suitabilities: {[r['suitable_for'] for r in commercial]}")

    # 3g. Final scores must be higher than base scores (i.e., re-ranking is active)
    marble = search_tiles("polished white marble tiles 60x60", n_results=3)
    check("Re-ranking is active — final_score != base_score for at least one result",
          any(r["final_score"] != r["base_score"] for r in marble))


# ─── LAYER 4: Diversity Algorithm ────────────────────────────────────────────
def layer4_diversity():
    print("\n[Layer 4] Diversity Algorithm")
    results = search_tiles("white polished marble tiles", n_results=3)
    series_names = [r["series_name"] for r in results]
    unique = len(set(series_names))
    check("Diversity — results come from at least 2 different series",
          unique >= 2, f"Series: {series_names}")


# ─── LAYER 5: Intent Classifier ──────────────────────────────────────────────
def layer5_intent():
    print("\n[Layer 5] Intent Classifier")
    time.sleep(12)  # Rate limit

    yes_cases = [
        "show me white marble tiles",
        "what tiles do you have for bathroom?",
        "need grey polished 60x60 for office",
    ]
    for q in yes_cases:
        time.sleep(12)
        result = requires_product_search(q)
        check(f"Intent YES — '{q[:40]}'", result is True)

    no_cases = [
        "hello",
        "how much does this tile cost?",
        "can I speak to a sales rep?",
    ]
    for q in no_cases:
        time.sleep(12)
        result = requires_product_search(q)
        check(f"Intent NO  — '{q[:40]}'", result is False)


# ─── LAYER 6: End-to-End Pipeline ────────────────────────────────────────────
def layer6_e2e():
    print("\n[Layer 6] End-to-End Pipeline (Search + Generate)")
    time.sleep(15)
    tiles = search_tiles("grey matte concrete tiles for living room", n_results=3)
    time.sleep(15)
    response = generate_tile_response("grey matte concrete tiles for living room", tiles)

    check("E2E — search returns tiles",              len(tiles) > 0, f"{len(tiles)} tiles")
    check("E2E — generate returns ai_summary",       bool(response.get("ai_summary")))
    check("E2E — recommended_tiles is a list",       isinstance(response.get("recommended_tiles"), list))
    check("E2E — recommended_tiles count <= 4",      len(response.get("recommended_tiles", [])) <= 4)
    check("E2E — recommended_tiles have sku field",
          all("sku" in t for t in response.get("recommended_tiles", [{"sku": ""}])))


# ─── LAYER 7: Refusal & Safety Guards ────────────────────────────────────────
def layer7_safety():
    print("\n[Layer 7] Safety & Refusal Guards")

    refusal_tests = [
        ("how much does the Lounge series cost?",   "Pricing refusal"),
        ("is RAK better than Kajaria?",             "Competitor refusal"),
        ("who won the 2022 World Cup?",             "Off-topic refusal"),
    ]
    for query, label in refusal_tests:
        time.sleep(15)
        tiles = search_tiles(query, n_results=3)
        time.sleep(15)
        response = generate_tile_response(query, tiles)
        tiles_returned = response.get("recommended_tiles", [])
        check(f"{label} — recommended_tiles is empty", len(tiles_returned) == 0,
              f"Returned {len(tiles_returned)} tiles")
        check(f"{label} — ai_summary is not empty", bool(response.get("ai_summary")))


# ─── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  RAK CERAMICS - FULL SYSTEM HEALTH CHECK")
    print("=" * 60)

    layer0_database()
    layer1_retrieval()
    layer2_threshold()
    layer3_reranking()
    layer4_diversity()
    layer5_intent()
    layer6_e2e()
    layer7_safety()

    # Summary
    total = len(results_log)
    passed = sum(1 for r in results_log if r["status"] == PASS)
    failed = total - passed

    print("\n" + "=" * 60)
    print("  HEALTH CHECK SUMMARY")
    print("=" * 60)
    print(f"  Total Checks : {total}")
    print(f"  Passed       : {passed}")
    print(f"  Failed       : {failed}")
    print(f"  Score        : {passed}/{total} ({round(passed/total*100)}%)")
    if failed > 0:
        print("\n  FAILURES:")
        for r in results_log:
            if r["status"] == FAIL:
                print(f"    - {r['label']}  {r['detail']}")
    print("=" * 60)
