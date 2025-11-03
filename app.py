import uvicorn
from fastapi import FastAPI, Request  # <-- PERUBAHAN 1
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from tts_with_rvc import TTS_RVC
from pathlib import Path
import logging

# --- 1. Setup & Model Loading (Runs ONCE on startup) ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "tauri://localhost", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
model_path = BASE_DIR / "models" / "Arona.pth"
index_path = BASE_DIR / "models" / "Arona.index"

logger.info("Loading TTS-RVC model...")
try:
    tts = TTS_RVC(
        model_path=str(model_path),
        index_path=str(index_path)
    )
    logger.info("Model loaded successfully.")
except Exception as e:
    logger.critical(f"CRITICAL: Failed to load model. Error: {e}")
    tts = None

# --- 2. Request Schema ---
class TTSRequest(BaseModel):
    text: str
    voice: str = "id-ID-GadisNeural"
    pitch: int = 6
    index_rate: float = 0.9
    tts_rate: float = 5

# --- 3. API Endpoint ---
@app.post("/generate_audio")
async def generate_audio_endpoint(request: TTSRequest, http_request: Request): # <-- PERUBAHAN 2
    if tts is None:
        logger.error("TTS model is not loaded. Cannot process request.")
        return {"error": "TTS model failed to load on startup"}, 500

    logger.info(f"Received request for text: {request.text}")
    try:
        tts.set_voice(request.voice)
        raw_path = tts(
            text=request.text,
            pitch=request.pitch,
            index_rate=request.index_rate,
            tts_rate=request.tts_rate
        )
        absolute_path = Path(raw_path).resolve()
        logger.info(f"Successfully generated audio at: {absolute_path}")
        
        # --- PERUBAHAN 3 ---
        # Menggunakan base_url dari request untuk membuat URL yang benar
        # secara dinamis, baik di lokal maupun di Codespaces.
        base_url = str(http_request.base_url)
        # Pastikan base_url diakhiri dengan / jika belum
        if not base_url.endswith('/'):
            base_url += '/'
            
        # Menggunakan f"{base_url}temp/..." alih-alih "http://127.0.0.1:12345/temp/..."
        return {"file_path": f"{base_url}temp/{absolute_path.name}"}
        # -------------------

    except Exception as e:
        logger.error(f"Error during TTS generation: {e}")
        return {"error": str(e)}, 500

# Pastikan direktori 'temp' ada
temp_dir = BASE_DIR / "temp"
temp_dir.mkdir(exist_ok=True)
app.mount("/temp", StaticFiles(directory=temp_dir), name="temp")

# --- 4. Run the Server ---
if __name__ == "__main__":
    logger.info("Starting server on http://0.0.0.0:12345") # <-- PERUBAHAN 4
    uvicorn.run(app, host="0.0.0.0", port=12345) # <-- PERUBAHAN 5
