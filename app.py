from fastapi import FastAPI, File, UploadFile, Header, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import time
import uvicorn

app = FastAPI()

UPLOAD_DIR = "uploaded_captures"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/captures", StaticFiles(directory=UPLOAD_DIR), name="captures")

SECRET_KEY = os.getenv("SASE_KEY", "fallback_secret_123")

@app.post("/upload")
async def upload_screenshot(
    file: UploadFile = File(...),
    authorization: str = Header(None)
):
    if authorization != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    timestamp = int(time.time())
    file_path = os.path.join(UPLOAD_DIR, f"capture_{timestamp}.jpg")

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    return {"status": "success", "filename": file_path, "bytes": len(contents)}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    files = sorted(os.listdir(UPLOAD_DIR), reverse=True)
    images_html = "".join([
        f'<div style="margin:10px;display:inline-block;border:1px solid #333;padding:10px;"><img src="/captures/{f}" style="max-width:200px;"/><p>{f}</p></div>'
        for f in files if f.endswith(".jpg")
    ]) or "<p>No captures yet.</p>"

    return f"<html><body style='background:#121212;color:#00ff00;'><h1>Dashboard</h1>{images_html}</body></html>"

if __name__ == "__main__":
    # Railway provides the PORT environment variable dynamically
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
