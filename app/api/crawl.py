"""
Crawler trigger API endpoints.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any
import asyncio

from app.core.logger import logger

router = APIRouter()


class CrawlRequest(BaseModel):
    """Crawl request model."""
    num_stories: int = 30
    force_refresh: bool = False


@router.post("/crawl/trigger")
async def trigger_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks
):
    """
    Manually trigger crawler to fetch latest articles.

    Args:
        num_stories: Number of stories to crawl (default: 30)
        force_refresh: Force re-crawl of existing articles

    Note: This runs in the background and returns immediately.
    """
    try:
        logger.info(f"Triggering crawler: {request.num_stories} stories")

        # Add crawl task to background
        background_tasks.add_task(
            run_crawler_task,
            request.num_stories,
            request.force_refresh
        )

        return {
            "message": "爬虫任务已启动",
            "num_stories": request.num_stories,
            "status": "running"
        }

    except Exception as e:
        logger.error(f"Trigger crawl error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_crawler_task(num_stories: int, force_refresh: bool):
    """
    Background task to run the crawler.

    Args:
        num_stories: Number of stories to crawl
        force_refresh: Force refresh flag
    """
    try:
        logger.info(f"Starting crawler task: {num_stories} stories")

        # Import here to avoid circular imports
        import subprocess
        import sys

        # Run crawler as subprocess
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.crawler.crawler",
                "-n",
                str(num_stories)
            ],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )

        if result.returncode == 0:
            logger.info("Crawler task completed successfully")
        else:
            logger.error(f"Crawler task failed: {result.stderr}")

    except subprocess.TimeoutExpired:
        logger.error("Crawler task timed out")
    except Exception as e:
        logger.error(f"Crawler task error: {e}")


@router.get("/crawl/status")
async def get_crawl_status():
    """
    Get crawler status and statistics.

    Returns information about the last crawl.
    """
    try:
        import os
        import json
        from app.core.config import DATA_DIR

        # Try to read crawled IDs
        crawled_ids_path = os.path.join(DATA_DIR, "crawled_ids.json")

        if not os.path.exists(crawled_ids_path):
            return {
                "status": "never_run",
                "message": "爬虫尚未运行"
            }

        with open(crawled_ids_path, "r") as f:
            crawled_ids = json.load(f)

        return {
            "status": "completed",
            "total_crawled": len(crawled_ids),
            "last_crawled_ids": list(crawled_ids)[-10:]  # Last 10
        }

    except Exception as e:
        logger.error(f"Get crawl status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
