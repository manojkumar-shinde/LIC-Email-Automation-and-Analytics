import uvicorn
import sys
import os

# Ensure path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    try:
        from app.main import app
        print("Successfully imported app.")
        uvicorn.run(app, host="0.0.0.0", port=8001)
    except Exception as e:
        print(f"Failed to start: {e}")
        import traceback
        traceback.print_exc()
