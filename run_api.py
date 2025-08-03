#!/usr/bin/env python3
"""
Pokreće API server
"""
import uvicorn
from src.api.main import app

if __name__ == "__main__":
    print("🚀 Pokrećem Serbian Estate Intelligence API...")
    print("📊 API dokumentacija: http://localhost:8000/docs")
    print("🌐 API root: http://localhost:8000/")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=True
    )