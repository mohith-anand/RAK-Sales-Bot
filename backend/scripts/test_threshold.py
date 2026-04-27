import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
from run.services.product_search_service import search_tiles

tests = [
    ("white polished marble tiles",   False),
    ("carpet for bedroom",            True),
    ("blue pizza oven tiles",         True),
    ("grey concrete floor tiles",     False),
    ("outdoor patio tiles",           False),
    ("sofa for living room",          True),
]

print()
print("="*55)
print("  FINAL THRESHOLD VALIDATION (0.70)")
print("="*55)
all_pass = True
for q, expect_empty in tests:
    r = search_tiles(q, n_results=2)
    got_empty = len(r) == 0
    ok = got_empty == expect_empty
    all_pass = all_pass and ok
    result = "empty" if got_empty else str(len(r)) + " tiles"
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}]  {q:<35} -> {result}")
print("="*55)
print(f"  Overall: {'ALL PASSED' if all_pass else 'SOME FAILED'}")
print("="*55)
