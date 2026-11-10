
import os
import cv2
import numpy as np
from dotenv import load_dotenv
from supabase import create_client
from insightface.app import FaceAnalysis
import os
import base64
import json
load_dotenv()
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

print("Key loaded:", key is not None)
print("Key length:", len(key) if key else 0)

if key and key.startswith("eyJ"):
    payload = key.split(".")[1]
    payload += "=" * (-len(payload) % 4)

    decoded = json.loads(
        base64.urlsafe_b64decode(payload)
    )

    print("JWT role:", decoded.get("role"))

# Load environment variables


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize InsightFace
print("Loading InsightFace model...")

app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)

app.prepare(ctx_id=-1, det_size=(640, 640))

print("Model loaded!")

# Student photos
students = [
    {"registration_number": "242114", "image": "student_photos/242114.JPEG"},
    {"registration_number": "242105", "image": "student_photos/242105.JPEG"},
    {"registration_number": "242119", "image": "student_photos/242119.JPEG"},
]

for student in students:

    registration_number = student["registration_number"]
    image_path = student["image"]

    print(f"\nProcessing student: {registration_number}")

    # Load image
    image = cv2.imread(image_path)

    if image is None:
        print(f"ERROR: Could not load image {image_path}")
        continue

    # Detect faces
    faces = app.get(image)

    if len(faces) != 1:
        print(f"ERROR: Expected exactly 1 face, found {len(faces)}")
        continue

    # Extract embedding
    embedding = faces[0].normed_embedding

    # Convert numpy array to Python list
    embedding_list = embedding.astype(float).tolist()

    print(f"Embedding generated: {len(embedding_list)} dimensions")

    # Update Supabase
    response = (
        supabase.table("students")
        .update({"face_embedding": embedding_list})
        .eq("registration_number", registration_number)
        .execute()
    )

    print(f"Successfully updated student {registration_number}")

print("\nAll processing completed!")
