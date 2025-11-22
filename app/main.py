"""
FastAPI main application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, articles, recommend, crawl
from app.core.config import APP_HOST, APP_PORT
from app.core.logger import logger

# Create FastAPI app
app = FastAPI(
    title="Hacker News RAG API",
    description="Semantic search and analysis for Hacker News articles",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(articles.router, prefix="/api", tags=["Articles"])
app.include_router(recommend.router, prefix="/api", tags=["Recommendations"])
app.include_router(crawl.router, prefix="/api", tags=["Crawler"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Hacker News RAG API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {APP_HOST}:{APP_PORT}")
    uvicorn.run(
        "app.main:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=True
    )
