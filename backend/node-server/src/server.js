import express from "express";
import dotenv from "dotenv";
import { supabase } from "./supabase.js";

dotenv.config({ path: "../../.env" });

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

app.get("/health", (req, res) => {
  res.json({
    status: "online",
    service: "rfid-face-verification-api",
  });
});

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

  const normalizedUid = rfid_uid_hex.toUpperCase();

  try {
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

app.listen(PORT, () => {
  console.log(`Node.js API running at http://localhost:${PORT}`);
});
