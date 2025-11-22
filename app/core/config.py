"""
Core configuration module for the HN RAG project.
Loads environment variables and defines application constants.
"""

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project Root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# ChromaDB Configuration
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./data/chromadb")
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "hacker_news")

# Hacker News API Configuration
HN_API_BASE_URL = os.getenv("HN_API_BASE_URL", "https://hacker-news.firebaseio.com/v0")
JINA_READER_BASE_URL = os.getenv("JINA_READER_BASE_URL", "https://r.jina.ai")

# Crawler Configuration
CRAWLER_SCHEDULE = os.getenv("CRAWLER_SCHEDULE", "0 7 * * *")
CRAWLER_MAX_STORIES = int(os.getenv("CRAWLER_MAX_STORIES", "30"))
CRAWLER_MAX_RETRIES = int(os.getenv("CRAWLER_MAX_RETRIES", "3"))
CRAWLER_TIMEOUT = int(os.getenv("CRAWLER_TIMEOUT", "30"))

# Comment Parsing Configuration
MAX_TOP_LEVEL_COMMENTS = int(os.getenv("MAX_TOP_LEVEL_COMMENTS", "10"))
MAX_REPLIES_PER_COMMENT = int(os.getenv("MAX_REPLIES_PER_COMMENT", "3"))
HIGH_SCORE_THRESHOLD = int(os.getenv("HIGH_SCORE_THRESHOLD", "20"))

# Application Settings
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# File Paths
USER_PROFILE_PATH = os.getenv("USER_PROFILE_PATH", "./data/user_profiles.json")
FAILED_ITEMS_PATH = os.getenv("FAILED_ITEMS_PATH", "./data/failed_items.json")
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "./logs/crawler.log")

# Topic Classification
TOPICS_STR = os.getenv(
    "TOPICS",
    "AI/ML,Programming Languages,Web Development,Databases,Security/Privacy,"
    "Startups/Business,Hardware/IoT,Science,Open Source,Career/Jobs"
)
TOPICS: List[str] = [topic.strip() for topic in TOPICS_STR.split(",")]

# Document Processing
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
MAX_COMMENT_LENGTH = int(os.getenv("MAX_COMMENT_LENGTH", "4000"))

# Validation
# Note: OPENAI_API_KEY validation is commented out for testing crawler modules
# Uncomment when using LLM features
# if not OPENAI_API_KEY:
#     raise ValueError("OPENAI_API_KEY environment variable is not set")
