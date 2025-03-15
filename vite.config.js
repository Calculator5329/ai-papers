import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig({
  base: "/ai-papers/", // ✅ Change this to match your GitHub repo name
  plugins: [react()],
})
