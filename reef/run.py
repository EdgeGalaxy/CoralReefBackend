import sys
sys.path.append("..")

from reef.api import app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, workers=1)