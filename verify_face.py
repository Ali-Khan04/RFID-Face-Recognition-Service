
import os
import ast
import cv2
import numpy as np

from dotenv import load_dotenv
from supabase import create_client
from insightface.app import FaceAnalysis

# ==========================================
# CONFIGURATION
# ==========================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Provisional threshold. Calibrate with real test samples.
SIMILARITY_THRESHOLD = 0.40

# ==========================================
# LOAD INSIGHTFACE
# ==========================================

print("Loading InsightFace...")

app = FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)

app.prepare(ctx_id=-1, det_size=(640, 640))

print("InsightFace loaded!")

# ==========================================
# RFID SIMULATION
# ==========================================

print("\n================================")
print("   RFID FACE VERIFICATION")
print("================================")

rfid_uid = input("\nEnter RFID UID: ").strip().upper()

# Fetch student from Supabase
response = (
    supabase.table("students")
    .select("full_name, registration_number, rfid_uid_hex, face_embedding")
    .eq("rfid_uid_hex", rfid_uid)
    .execute()
)

if not response.data:
    print("\n❌ RFID CARD NOT REGISTERED")
    exit()

student = response.data[0]

student_name = student["full_name"]
registration_number = student["registration_number"]

stored_embedding = student["face_embedding"]

# pgvector can be returned as a string
if isinstance(stored_embedding, str):
    stored_embedding = ast.literal_eval(stored_embedding)

stored_embedding = np.array(
    stored_embedding,
    dtype=np.float32
)

if stored_embedding.shape != (512,):
    print("ERROR: Invalid stored embedding dimensions")
    exit()

print("\nStudent Found!")
print("Name:", student_name)
print("Registration:", registration_number)

print("\nOpening webcam...")
print("Press Q to quit.")

# ==========================================
# WEBCAM
# ==========================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: Could not open webcam")
    exit()

while True:

    ret, frame = cap.read()

    if not ret:
        print("ERROR: Failed to capture frame")
        break

    faces = app.get(frame)

    status = "NO FACE DETECTED"
    color = (0, 0, 255)

    if len(faces) == 1:

        face = faces[0]

        # Generate current face embedding
        current_embedding = face.normed_embedding.astype(
            np.float32
        )

        # Cosine similarity between normalized embeddings
        similarity = float(
            np.dot(stored_embedding, current_embedding)
        )

        similarity = max(-1.0, min(1.0, similarity))

        # Face verification
        if similarity >= SIMILARITY_THRESHOLD:

            status = "MATCH - VERIFIED"
            color = (0, 255, 0)

        else:

            status = "NO MATCH - REJECTED"
            color = (0, 0, 255)

        # Face bounding box
        bbox = face.bbox.astype(int)

        x1, y1, x2, y2 = bbox

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            color,
            2
        )

        cv2.putText(
            frame,
            f"Similarity: {similarity:.3f}",
            (x1, y1 - 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2
        )

    elif len(faces) > 1:

        status = "MULTIPLE FACES - REJECTED"
        color = (0, 0, 255)

    # Display student
    cv2.putText(
        frame,
        f"Student: {student_name}",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    # Display verification status
    cv2.putText(
        frame,
        status,
        (20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        color,
        2
    )

    cv2.imshow(
        "RFID Face Verification",
        frame
    )

    # Quit with Q
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

print("\nVerification session ended.")
