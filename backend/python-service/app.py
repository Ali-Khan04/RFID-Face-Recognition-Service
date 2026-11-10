
import os
import json
import secrets

import cv2
import numpy as np

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from insightface.app import FaceAnalysis

# CONFIGURATION
load_dotenv()

SERVICE_TOKEN = os.getenv("FACE_SERVICE_TOKEN")

if not SERVICE_TOKEN:
    raise RuntimeError("FACE_SERVICE_TOKEN is missing from .env")

app = FastAPI(
    title="RFID Face Recognition Service",
    version="1.0.0"
)

# INSIGHTFACE INITIALIZATION
print("Loading InsightFace model...")

face_analyzer = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)

face_analyzer.prepare(
    ctx_id=-1,
    det_size=(640, 640)
)

print("InsightFace model loaded!")


# AUTHENTICATION
def authenticate_service(token: str | None):

    if token is None or not secrets.compare_digest(
        token, SERVICE_TOKEN
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized service request"
        )


# HEALTH CHECK
@app.get("/health")
def health_check():

    return {
        "status": "online",
        "service": "face-recognition"
    }



# FACE VERIFICATION
@app.post("/verify-face")
async def verify_face(
    image: UploadFile = File(...),
    reference_embedding: str = Form(...),
    x_service_token: str | None = Header(default=None)
):

    # Authenticate Node.js backend
    authenticate_service(x_service_token)

    # Validate uploaded image
    if image.content_type not in ["image/jpeg", "image/jpg"]:
        raise HTTPException(
            status_code=400,
            detail="Only JPEG images are supported"
        )

    # Read image bytes
    image_bytes = await image.read()

    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty image received"
        )

    # Decode JPEG into OpenCV image
    image_array = np.frombuffer(
        image_bytes,
        dtype=np.uint8
    )

    frame = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR
    )

    if frame is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid image"
        )

    # Parse stored embedding from Node.js
    try:
        reference = np.array(
            json.loads(reference_embedding),
            dtype=np.float32
        )

    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid reference embedding"
        )

    # Validate dimensions
    if reference.shape != (512,):
        raise HTTPException(
            status_code=400,
            detail="Reference embedding must have 512 dimensions"
        )

    if not np.all(np.isfinite(reference)):
        raise HTTPException(
            status_code=400,
            detail="Reference embedding contains invalid values"
        )

    # Detect faces
    faces = face_analyzer.get(frame)

    # No face detected
    if len(faces) == 0:

        return {
            "success": True,
            "faces_detected": 0,
            "status": "NO_FACE_DETECTED",
            "similarity": None
        }

    # Multiple faces detected
    if len(faces) > 1:

        return {
            "success": True,
            "faces_detected": len(faces),
            "status": "MULTIPLE_FACES",
            "similarity": None
        }

    # Generate current face embedding
    current_embedding = faces[0].normed_embedding.astype(
        np.float32
    )

    # Normalize reference embedding
    reference_norm = np.linalg.norm(reference)

    if reference_norm == 0:
        raise HTTPException(
            status_code=400,
            detail="Reference embedding has zero norm"
        )

    reference = reference / reference_norm

    # Calculate cosine similarity
    similarity = float(
        np.dot(reference, current_embedding)
    )

    similarity = max(-1.0, min(1.0, similarity))

    # Return score; Node.js decides the threshold
    return {
        "success": True,
        "faces_detected": 1,
        "status": "FACE_PROCESSED",
        "similarity": similarity
    }
