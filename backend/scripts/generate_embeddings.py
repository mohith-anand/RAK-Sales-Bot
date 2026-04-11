import os
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb
import time
from google.api_core import exceptions

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# --- Dynamic Directory Pathing ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # .../backend/scripts
BACKEND_DIR = os.path.dirname(BASE_DIR)              # .../backend

CSV_PATH = os.path.join(BACKEND_DIR, "data", "processed_csv", "products_cleaned.csv")
CHROMA_PATH = os.path.join(BACKEND_DIR, "data", "vector_db")

EMBEDDING_MODEL = "models/gemini-embedding-2-preview"
BATCH_SIZE = 50

# Load CSV
df = pd.read_csv(CSV_PATH).fillna("")

# Create persistent Chroma client
client = chromadb.PersistentClient(path=CHROMA_PATH)

# Use cosine similarity for Gemini v2 embeddings
collection = client.get_or_create_collection(
    name="rak_tiles_products",
    metadata={"hnsw:space": "cosine"}
)

print(f"Starting vectorization. Current collection count: {collection.count()}")

for i in tqdm(range(0, len(df), BATCH_SIZE), desc="Generating embeddings"):
    batch = df.iloc[i:i + BATCH_SIZE]

    # Remove rows with empty embedding text
    filtered_batch = batch[
        batch["embedding_text"].astype(str).str.strip() != ""
    ].copy()

    if filtered_batch.empty:
        continue

    # Prepare document texts with Gemini 2 prefix
    input_texts = [
        f"task: retrieval_document | {str(text).strip()}"
        for text in filtered_batch["embedding_text"]
    ]

    max_retries = 3
    retry_count = 0
    while retry_count < max_retries:
        try:
            # Batch embedding request
            result = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=input_texts,
                task_type="retrieval_document"
            )

            # --- ROBUST EMBEDDING EXTRACTION ---
            if "embeddings" in result:
                embeddings = result["embeddings"]
            elif "embedding" in result:
                data = result["embedding"]
                embeddings = data if isinstance(data[0], list) else [data]
            else:
                print(f"\n[Error] Unexpected API response at row {i}. Keys: {result.keys()}")
                break

            ids = [
                str(row["sku_code"]).strip() if str(row["sku_code"]).strip() else str(idx)
                for idx, row in filtered_batch.iterrows()
            ]

            documents = [
                text.replace("task: retrieval_document | ", "")
                for text in input_texts
            ]

            metadatas = []
            for _, row in filtered_batch.iterrows():
                metadatas.append({
                    "category": str(row.get("category", "")),
                    "series_name": str(row.get("series_name", "")),
                    "tile_type": str(row.get("tile_type", "")),
                    "color": str(row.get("color", "")),
                    "surface": str(row.get("surface", "")),
                    "size_cm": str(row.get("size_cm", "")),
                    "size_inches": str(row.get("size_inches", "")),
                    "sku_code": str(row.get("sku_code", "")),
                    "application": str(row.get("application", "")),
                    "suitable_for": str(row.get("suitable_for", "")),
                    "page_number": str(row.get("page_number", "")),
                    "image_path": str(row.get("image_path", ""))
                })

            if len(ids) == len(embeddings):
                collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
            break # Success, exit retry loop

        except exceptions.ResourceExhausted as e:
            retry_count += 1
            wait_time = 30 * retry_count
            print(f"\n[Quota reached] Batch {i}. Waiting {wait_time}s... (Attempt {retry_count}/{max_retries})")
            time.sleep(wait_time)
        except Exception as e:
            print(f"\nError in batch starting at row {i}: {e}")
            break

# --- FINAL VERIFICATION ---
print(f"\nSuccess! Chroma DB updated.")
print(f"Final collection count: {collection.count()}")
print(f"Vector Store Location: {CHROMA_PATH}")