import multiprocessing
import uvicorn
import time
import os
import sys
import traceback
from datetime import datetime

# Ensure src path is in pythonpath
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Ensure logs directory exists
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
STARTUP_LOG = os.path.join(LOG_DIR, 'startup.log')

def _log_startup(msg: str):
    ts = datetime.now().isoformat()
    line = f"[{ts}] {msg}\n"
    with open(STARTUP_LOG, 'a', encoding='utf-8') as f:
        f.write(line)
    print(msg)

# Define wrapper functions that import dependencies INSIDE the process
# This prevents top-level imports from running in every subprocess on Windows

def run_api():
    # Deferred import to keep main process clean
    from app.main import app
    _log_startup("DEBUG: API Process Starting...")
    sys.stdout.flush()
    uvicorn.run(app, host="127.0.0.1", port=8001, reload=False)

def run_ingestor():
    from app import ingestor
    ingestor.start_loop()

def run_worker():
    from app import worker
    worker.start_loop()

if __name__ == "__main__":
    try:
        # Now we can import these for initialization
        from app import database, rag

        _log_startup("--------------------------------------------------")
        _log_startup("   LIC EMAIL INTELLIGENCE PLATFORM (LOCAL)        ")
        _log_startup("--------------------------------------------------")

        _log_startup("[1/2] Initializing Database...")
        database.init_db()

        _log_startup("[2/2] Checking for Policy Documents (RAG)...")
        try:
            rag.ingest_docs()
        except Exception as e:
            _log_startup(f"RAG ingestion failed: {e}")
            _log_startup(traceback.format_exc())

        _log_startup("\nStarting Services...")
    except Exception as e:
        _log_startup(f"Startup failed: {e}")
        _log_startup(traceback.format_exc())
        raise
    
    # Create processes
    p_api = multiprocessing.Process(target=run_api, name="API_Server")
    # p_ingestor = multiprocessing.Process(target=run_ingestor, name="Ingestor")  # Disabled - causing startup issues
    p_worker = multiprocessing.Process(target=run_worker, name="Worker")

    # Start processes
    p_api.start()
    # p_ingestor.start()  # Disabled
    p_worker.start()

    try:
        while True:
            time.sleep(1)
            if not p_api.is_alive():
                _log_startup("API Server died!")
                break
    except KeyboardInterrupt:
        _log_startup("\nStopping services...")
    finally:
        # p_ingestor.terminate()
        p_worker.terminate()
        p_api.terminate()
        # p_ingestor.join()
        p_worker.join()
        p_api.join()
        _log_startup("All services stopped.")
