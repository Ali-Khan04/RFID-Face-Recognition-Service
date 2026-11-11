import express from "express";
import dotenv from "dotenv";
import multer from "multer";
import { supabase } from "./supabase.js";

dotenv.config({ path: "../../.env" });

const app = express();
const PORT = process.env.PORT || 3000;
const FACE_SERVICE_URL = process.env.FACE_SERVICE_URL;
const FACE_SERVICE_TOKEN = process.env.FACE_SERVICE_TOKEN;
const FACE_MATCH_THRESHOLD = Number(process.env.FACE_MATCH_THRESHOLD || 0.4);

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 5 * 1024 * 1024 },
});

app.use(express.json());

// Health check endpoint
app.get("/health", (req, res) => {
  res.json({
    status: "online",
    service: "rfid-face-verification-api",
  });
});

//api/students/lookup endpoint for student lookup by RFID UID
app.post("/api/students/lookup", async (req, res) => {
  const { rfid_uid_hex } = req.body;

  if (
    typeof rfid_uid_hex !== "string" ||
    !/^[0-9a-fA-F]{12}$/.test(rfid_uid_hex)
  ) {
    return res.status(400).json({
      success: false,
      message: "Invalid RFID UID. Expected 12 hexadecimal characters.",
    });
  }

  try {
    const { data: student, error } = await supabase
      .from("students")
      .select(
        "id, full_name, registration_number, rfid_uid_hex, face_embedding",
      )
      .eq("rfid_uid_hex", rfid_uid_hex.toUpperCase())
      .maybeSingle();

    if (error) {
      console.error("Supabase lookup error:", error.message);
      return res.status(500).json({
        success: false,
        message: "Database lookup failed",
      });
    }

    if (!student) {
      return res.status(404).json({
        success: false,
        message: "Student not found",
      });
    }

    if (!student.face_embedding) {
      return res.status(409).json({
        success: false,
        message: "Student face embedding is not registered",
      });
    }

    return res.json({
      success: true,
      student: {
        id: student.id,
        full_name: student.full_name,
        registration_number: student.registration_number,
        rfid_uid_hex: student.rfid_uid_hex,
      },
      face_embedding_present: true,
    });
  } catch (error) {
    console.error("Unexpected lookup error:", error.message);
    return res.status(500).json({
      success: false,
      message: "Internal server error",
    });
  }
});

//api/verify endpoint for face verification

app.post("/api/verify", upload.single("image"), async (req, res) => {
  const { rfid_uid_hex } = req.body;

  if (
    typeof rfid_uid_hex !== "string" ||
    !/^[0-9a-fA-F]{12}$/.test(rfid_uid_hex)
  ) {
    return res.status(400).json({
      success: false,
      message: "Invalid RFID UID",
    });
  }

  if (!req.file) {
    return res.status(400).json({
      success: false,
      message: "JPEG image is required",
    });
  }

  if (req.file.mimetype !== "image/jpeg") {
    return res.status(400).json({
      success: false,
      message: "Only JPEG images are supported",
    });
  }

  if (!FACE_SERVICE_URL || !FACE_SERVICE_TOKEN) {
    return res.status(500).json({
      success: false,
      message: "Face service configuration is missing",
    });
  }

  try {
    const normalizedUid = rfid_uid_hex.toUpperCase();

    const { data: student, error } = await supabase
      .from("students")
      .select(
        "id, full_name, registration_number, rfid_uid_hex, face_embedding",
      )
      .eq("rfid_uid_hex", normalizedUid)
      .maybeSingle();

    if (error) {
      console.error("Supabase lookup error:", error.message);
      return res.status(500).json({
        success: false,
        message: "Database lookup failed",
      });
    }

    if (!student) {
      return res.status(404).json({
        success: false,
        status: "STUDENT_NOT_FOUND",
      });
    }

    if (!student.face_embedding) {
      return res.status(409).json({
        success: false,
        status: "EMBEDDING_NOT_REGISTERED",
      });
    }

    const formData = new FormData();

    formData.append(
      "image",
      new Blob([req.file.buffer], { type: "image/jpeg" }),
      "capture.jpg",
    );

    // Convert the embedding to a JSON string
    const referenceEmbedding =
      typeof student.face_embedding === "string"
        ? student.face_embedding
        : JSON.stringify(student.face_embedding);

    formData.append("reference_embedding", referenceEmbedding);

    const faceResponse = await fetch(`${FACE_SERVICE_URL}/verify-face`, {
      method: "POST",
      headers: {
        "x-service-token": FACE_SERVICE_TOKEN,
      },
      body: formData,
      signal: AbortSignal.timeout(15000),
    });

    const faceResult = await faceResponse.json();

    if (!faceResponse.ok) {
      console.error("Face service error:", faceResult);
      return res.status(502).json({
        success: false,
        message: "Face verification service failed",
      });
    }

    if (faceResult.status !== "FACE_PROCESSED") {
      return res.json({
        success: true,
        status: faceResult.status,
        matched: false,
        faces_detected: faceResult.faces_detected,
        student: {
          full_name: student.full_name,
          registration_number: student.registration_number,
        },
      });
    }

    const matched = faceResult.similarity >= FACE_MATCH_THRESHOLD;

    return res.json({
      success: true,
      status: matched ? "MATCH" : "NO_MATCH",
      matched,
      similarity: faceResult.similarity,
      threshold: FACE_MATCH_THRESHOLD,
      student: {
        full_name: student.full_name,
        registration_number: student.registration_number,
      },
    });
  } catch (error) {
    console.error("Verification error:", error.message);

    return res.status(502).json({
      success: false,
      message: "Unable to complete face verification",
    });
  }
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`Node.js API running on port ${PORT}`);
});
