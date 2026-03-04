import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // No proxy to localhost. Chat runs in Streamlit (streamlit run streamlit_app.py)
    // or via FastAPI (uvicorn backend.app:app --host 127.0.0.1 --port 8000) if you need the React UI.
  }
});

