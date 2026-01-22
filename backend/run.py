import multiprocessing
import uvicorn
import time
import os
import sys

# Ensure src path is in pythonpath
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Define wrapper functions that import dependencies INSIDE the process
# This prevents top-level imports from running in every subprocess on Windows

def run_api():
    # Deferred import to keep main process clean
    from app.main import app
    print("DEBUG: API Process Starting...")
    sys.stdout.flush()
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)

def run_ingestor():
    from app import ingestor
    ingestor.start_loop()

def run_worker():
    from app import worker
    worker.start_loop()

if __name__ == "__main__":
    # Now we can import these for initialization
    from app import database, rag
    
    print("--------------------------------------------------")
    print("   LIC EMAIL INTELLIGENCE PLATFORM (LOCAL)        ")
    print("--------------------------------------------------")
    
    print("[1/2] Initializing Database...")
    database.init_db()
    
    print("[2/2] Checking for Policy Documents (RAG)...")
    rag.ingest_docs()
    
    print("\nStarting Services...")
    
    # Create processes
    p_api = multiprocessing.Process(target=run_api, name="API_Server")
    # p_ingestor = multiprocessing.Process(target=run_ingestor, name="Ingestor")
    p_worker = multiprocessing.Process(target=run_worker, name="Worker")

    # Start processes
    p_api.start()
    # p_ingestor.start() # Disabled per user request
    p_worker.start()

    try:
        while True:
            time.sleep(1)
            if not p_api.is_alive():
                print("API Server died!")
                break
    except KeyboardInterrupt:
        print("\nStopping services...")
    finally:
        # p_ingestor.terminate()
        p_worker.terminate()
        p_api.terminate()
        # p_ingestor.join()
        p_worker.join()
        p_api.join()
        print("All services stopped.")
