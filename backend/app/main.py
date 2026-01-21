from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router
from app import database, rag
import logging

# Setup Logger
logger = logging.getLogger("Main")
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application starting up...")
    logger.info("Initializing Database...")
    database.init_db()
    
    # In a production app, heavy tasks like RAG ingestion might be delegated to a worker 
    # or run in the background to avoid blocking startup. 
    # For this local setup, we'll keep it simple but acknowledge the tradeoff.
    logger.info("Checking for Policy Documents (RAG)...")
    rag.ingest_docs()
    
    yield
    
    # Shutdown
    logger.info("Application shutting down...")

app = FastAPI(
    title="LIC Email Intelligence Platform",
    description="Local-first AI platform for processing and analyzing emails.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
# In production, load these from environment variables
origins = [
    "http://localhost:5173",  # Vite Frontend
    "http://127.0.0.1:5173",
    "*" # Permissive for local dev, restrict in prod
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api", tags=["API"])

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "app": "LIC Platform", "version": "1.0.0"}
