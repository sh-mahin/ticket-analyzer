import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite env VITE_API_BASE_URL is compile-time baked by the Docker build.
// In Phase 0 the backend is reached directly on its host port (8000).
// In Phase 3 we switch the build arg to "/api" and proxy via nginx.
export default defineConfig({
  plugins: [react()],
});
