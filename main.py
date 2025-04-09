from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import tempfile, os, openai, exifread
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VerificationRequest(BaseModel):
    text: str

class ImageURLRequest(BaseModel):
    url: str

@app.post("/verify/news")
async def verify_news(data: VerificationRequest):
    return {"verdict": "Likely Genuine", "confidence": 88, "sources": [{"name": "Reuters", "url": "https://reuters.com"}]}

@app.post("/verify/claim")
async def verify_claim(data: VerificationRequest):
    prompt = f"""Analyze the claim below and respond with JSON: {data.text}"""
    try:
        res = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "You are a fact-checking assistant."}, {"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return eval(res.choices[0].message.content.strip())
    except Exception as e:
        return {"error": str(e)}

@app.post("/verify/image")
async def verify_image_from_url(data: ImageURLRequest):
    return {
        "verdict": "Possibly Edited",
        "notes": ["EXIF data not available via URL."],
        "sources": [{"name": "Reverse Search", "url": f"https://images.google.com/searchbyimage?image_url={data.url}"}]
    }

@app.post("/upload/image")
async def upload_image(file: UploadFile = File(...)):
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.write(await file.read())
    temp_file.close()
    verdict = "Genuine"
    notes = []
    try:
        with open(temp_file.name, 'rb') as f:
            tags = exifread.process_file(f)
            if "Image Software" in tags:
                notes.append(f"Edited using: {tags['Image Software']}")
                verdict = "Possibly Edited"
            if "EXIF DateTimeOriginal" not in tags:
                notes.append("Missing original timestamp.")
    except Exception as e:
        notes.append(str(e))
    os.remove(temp_file.name)
    return {"verdict": verdict, "notes": notes or ["No edits found."], "filename": file.filename}

@app.get("/")
async def root():
    return {"message": "TruthCheck backend is live."}
