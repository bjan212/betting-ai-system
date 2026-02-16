import os
import sys
import traceback

# Ensure the project root is in the path
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)
os.chdir(root)

try:
    from src.api.main import app
except Exception as e:
    # Fallback app that shows the error for debugging
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    app = FastAPI(title="Betting AI System API (fallback)")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
    
    @app.get("/")
    @app.get("/health")
    @app.get("/api/v1/betting/top3")
    async def fallback_handler():
        return {
            "status": "error",
            "message": "App failed to load",
            "error": error_msg,
            "python_path": sys.path[:5],
            "cwd": os.getcwd(),
            "root": root,
            "files": os.listdir(root)[:20] if os.path.isdir(root) else "not a dir"
        }
