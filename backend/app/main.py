from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router
from app import database, rag, worker
import logging
import asyncio

# Setup Logger
logger = logging.getLogger("Main")
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application starting up...")
    logger.info("Initializing Database...")
    database.init_db()
    
    logger.info("Checking for Policy Documents (RAG)...")
    # Run RAG ingestion in a thread to avoid blocking
    await asyncio.to_thread(rag.ingest_docs)
    
    # Create worker task reference
    worker_task = None
    
    # Define worker coroutine
    async def start_worker():
        await asyncio.sleep(1)  # Brief delay to ensure server is ready
        logger.info("Starting email processing worker...")
        await asyncio.to_thread(worker.start_loop)
    
    # Start worker in background
    worker_task = asyncio.create_task(start_worker())
    logger.info("Email processing worker task created")
    
    yield
    
    # Shutdown
    logger.info("Application shutting down...")
    if worker_task and not worker_task.done():
        worker_task.cancel()

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
