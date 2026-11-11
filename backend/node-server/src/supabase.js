import { createClient } from "@supabase/supabase-js";
import dotenv from "dotenv";
import ws from "ws";

dotenv.config({ path: "../../.env" });

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !supabaseServiceRoleKey) {
  throw new Error("Supabase environment variables are missing");
}

export const supabase = createClient(supabaseUrl, supabaseServiceRoleKey, {
  realtime: {
    transport: ws,
  },
});
