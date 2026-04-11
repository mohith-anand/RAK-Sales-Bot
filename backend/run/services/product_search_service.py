import os
import re
import chromadb
import google.generativeai as genai
from dotenv import load_dotenv
# Load API Key from project root .env (relative to backend/run/services)
from pathlib import Path
dotenv_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(dotenv_path)
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(f"GEMINI_API_KEY not set. Checked: {dotenv_path}")

genai.configure(api_key=api_key)

# --- CRITICAL PATH ALIGNMENT ---
# BASE_DIR is 'backend/run/services'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# PROJECT_ROOT is 'backend/' (Up two levels from services)
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))

# Path to the vector database in project/data/vector_db
CHROMA_PATH = os.path.join(PROJECT_ROOT, "data", "vector_db")
EMBEDDING_MODEL = "models/gemini-embedding-2-preview"

# Initialize ChromaDB
client = chromadb.PersistentClient(path=CHROMA_PATH)

try:
    collection = client.get_collection("rak_tiles_products")
    print(f"✅ Connected to Database: {collection.count()} products found.")
except Exception as e:
    print(f"❌ Error: Could not find collection. Ensure you ran build_vector_db.py first. {e}")
    exit()

def search_tiles(user_query: str, n_results: int = 3):
    query_lower = user_query.lower()

    # 1. Generate Query Embedding
    formatted_query = f"task: retrieval_query | {user_query}"
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=formatted_query,
        task_type="retrieval_query"
    )

    query_embedding = (
        result["embedding"]
        if "embedding" in result
        else result["embeddings"][0]
    )

    # 2. Vector Search (Fetch 60 candidates for re-ranking)
    raw_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=60
    )

    processed_list = []

    # Regex to catch sizes like '60x60' or '30x60'
    size_match = re.search(r'(\d{2,3}x\d{2,3})', query_lower)
    target_size = size_match.group(1) if size_match else None

    # 3. Hybrid Re-ranking Logic
    for i in range(len(raw_results["ids"][0])):
        metadata = raw_results["metadatas"][0][i]
        dist = raw_results["distances"][0][i]

        base_similarity = round(1 - dist, 4)
        final_score = base_similarity

        # Extract metadata fields safely
        series_name_raw = metadata.get("series_name", "").lower()
        category_raw = metadata.get("category", "").lower()
        surface = metadata.get("surface", "").lower()
        color = metadata.get("color", "").lower()
        suitable = metadata.get("suitable_for", "").lower()
        application = metadata.get("application", "").lower()
        tile_size_raw = metadata.get("size_cm", "").lower().replace(" ", "")

        # --- Keyword Flags ---
        polished_query = any(word in query_lower for word in ["polished", "gloss", "shiny", "reflective", "high gloss"])
        matt_query = any(word in query_lower for word in ["matt", "matte", "natural"])
        outdoor_query = any(word in query_lower for word in ["outdoor", "exterior", "patio", "garden"])
        office_query = any(word in query_lower for word in ["office", "commercial", "workspace"])
        wall_query = "wall" in query_lower
        floor_query = "floor" in query_lower

        # --- Rule 1: Material Look (CRITICAL) ---
        material_keywords = {
            "marble": "marble",
            "concrete": "concrete",
            "stone": "stone",
            "wood": "wood",
            "metal": "metal",
            "resin": "resin",
            "slate": "stone",
            "cement": "concrete"
        }

        requested_material = None
        for kw, material in material_keywords.items():
            if kw in query_lower:
                requested_material = material
                # Boost if category or series name contains the requested material

                if material in category_raw or material in series_name_raw:
                    final_score += 0.85
                elif material in metadata.get("embedding_text", "").lower():
                    final_score += 0.45
                else:
                    # STRICT PENALTY: Highly downvote if it doesn't contain the requested material
                    final_score -= 1.5 
                
                # Double boost for exact material category match
                if material == category_raw:
                    final_score += 0.50

        # --- Rule 2: Exact Series Name Match ---
        series_name = metadata.get("series_name", "").lower()
        if series_name and series_name in query_lower:
            final_score += 1.0  # Huge boost for specific collection mention

        # --- Rule 2: Surface Finish (STRICT) ---
        if polished_query:
            if "polished" in surface: final_score += 0.50
            elif "matt" in surface: final_score -= 1.5 # STRICT PENALTY
        
        if matt_query:
            if "matt" in surface: final_score += 0.40
            elif "polished" in surface: final_score -= 1.5 # STRICT PENALTY

        # --- Rule 3: Color Grouping (STRICT) ---
        color_groups = {
            "white_light": ["white", "active white", "supreme white", "white venato", "calacatta", "ivory", "cream", "bone"],
            "grey_silver": ["grey", "gray", "silver grey", "ash", "slate grey", "warm grey", "platinum"],
            "dark_black": ["black", "anthracite", "charcoal", "dark grey", "pitch black", "graphite", "dark"],
            "beige_warm": ["beige", "taupe", "sand", "summer sand", "brown"],
            "blue_cool": ["blue", "oceanic", "azure"]
        }

        # Map queries to color groups
        requested_color_group = None
        for group_name, colors in color_groups.items():
            if any(c in query_lower for c in colors):
                requested_color_group = group_name
                break

        if requested_color_group:
            # Check if the tile's color belongs to the requested group
            if any(c in color for c in color_groups[requested_color_group]):
                final_score += 0.50
            else:
                final_score -= 1.5 # STRICT PENALTY for color mismatch
        elif color in query_lower and len(color) > 2:
            # Fallback for exact color name matches not in groups
            final_score += 0.25

        # --- Rule 4: Aesthetics (Minimal/Contemporary) ---
        minimal_query = any(word in query_lower for word in ["minimal", "sleek", "modern", "contemporary", "simple"])
        if minimal_query:
            # Boost specific collections known for minimal look
            if any(word in series_name_raw for word in ["lounge", "loft", "basic", "revive", "industrial"]):
                final_score += 0.50
            elif any(word in category_raw for word in ["concrete", "cement", "resin"]):
                final_score += 0.30

        # --- Rule 5: Size Match ---
        if target_size and target_size in tile_size_raw:
            final_score += 0.40

        # --- Rule 6: Usage (Commercial vs Domestic) ---
        commercial_query = any(word in query_lower for word in ["commercial", "heavy usage", "office", "mall", "public"])
        heavy_commercial_query = "heavy" in query_lower and "commercial" in query_lower
        
        # Give Lounge an explicit boost for premium minimal searches
        if minimal_query and "lounge" in series_name_raw:
            final_score += 0.15

        if heavy_commercial_query:
            if "heavy commercial" in suitable:
                final_score += 0.80 # Stronger boost for heavy commercial
            elif "commercial" in suitable:
                final_score += 0.30
        elif commercial_query:
            if "heavy commercial" in suitable:
                final_score += 0.60 # Heavy commercial is still premium for general commercial
            elif "commercial" in suitable:
                final_score += 0.50
        
        if "domestic" in query_lower and "domestic" in suitable:
            final_score += 0.20

        # --- Image Path Handling ---
        raw_image_path = metadata.get("image_path", "")
        # Clean the path: it might look like './extracted_images/FILENAME.jpg' or be 'NO MATCH'
        # We just want the filename to serve it via our /images mount
        image_filename = None
        if raw_image_path and "NO MATCH" not in raw_image_path:
            image_filename = os.path.basename(raw_image_path)
        
        # --- Compile Result Object ---
        processed_list.append({
            "category": metadata.get("category", "N/A"),
            "series_name": metadata.get("series_name", "Unknown"),
            "color": metadata.get("color", "N/A"),
            "surface": metadata.get("surface", "N/A"),
            "size_cm": metadata.get("size_cm", "N/A"),
            "application": application,
            "suitable_for": suitable,
            "sku": raw_results["ids"][0][i],
            "page_number": metadata.get("page_number", ""),
            "image_path": image_filename if image_filename else "placeholder-tile.jpg",
            "base_score": round(base_similarity, 4),
            "final_score": round(final_score, 4)
        })

    # 4. Final Sort and return top n
    sorted_results = sorted(
        processed_list,
        key=lambda x: x["final_score"],
        reverse=True
    )

    # 5. Diversification (High Recall spread)
    diversified_results = []
    seen_series = {}
    
    # First pass: try to get up to 2 items per series (encourages variety)
    for res in sorted_results:
        s_name = res["series_name"]
        if seen_series.get(s_name, 0) < 2:
            diversified_results.append(res)
            seen_series[s_name] = seen_series.get(s_name, 0) + 1
        if len(diversified_results) >= n_results:
            break
            
    # If we didn't fulfill the quota (because we had too few unique series), fill with whatever is left
    if len(diversified_results) < n_results:
        for res in sorted_results:
            if res not in diversified_results:
                diversified_results.append(res)
            if len(diversified_results) >= n_results:
                break

    return diversified_results

if __name__ == "__main__":
    print("\n" + "="*60)
    print(" RAK CERAMICS - TILE SEARCH ENGINE")
    print(f" DB Path: {CHROMA_PATH}")
    print("="*60)
    
    while True:
        query = input("\nSearch (e.g., 'grey polished 60x60') or 'exit': ")
        if query.lower() in ['exit', 'quit']:
            break
            
        results = search_tiles(query, n_results=3)
        
        if not results:
            print("No tiles matched your search.")
            continue

        for i, tile in enumerate(results):
            print(f"\n[{i+1}] {tile['series_name'].upper()} | SKU: {tile['sku']}")
            print(f"    Color: {tile['color']} | Finish: {tile['surface']} | Size: {tile['size_cm']}")
            print(f"    App: {tile['application']} | Suitable: {tile['suitable_for']}")
            print(f"    Scores: [AI: {tile['base_score']}] -> [Final: {tile['final_score']}]")
            print("-" * 60)