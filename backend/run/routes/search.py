from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from run.services.product_search_service import search_tiles
from run.services.gemini_service import generate_tile_response, requires_product_search

router = APIRouter()

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    history: list = Field(default=[], max_length=20)
    n_results: int = Field(default=5, ge=1, le=20)

@router.post("/search")
def search_products(request: SearchRequest):
    try:
        results = []
        
        # Smartly determine if a product search is needed for this query
        if requires_product_search(user_query=request.query, history=request.history):
            # 1. Execute the vector search and re-ranking
            results = search_tiles(
                user_query=request.query,
                n_results=request.n_results
            )

        # 2. Generate the AI sales assistant response using Gemini 2.5 Flash
        ai_response = generate_tile_response(
            user_query=request.query,
            tile_results=results,
            history=request.history
        )

        # 3. Return the combined data
        return {
            "query": request.query,
            "count": len(results),
            "ai_response": ai_response,
            "results": results
        }
    except Exception as e:
        # Log internally but do not expose raw exception details to the client
        print(f"[ERROR] /api/search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again later.")
