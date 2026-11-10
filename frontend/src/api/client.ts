import axios from 'axios';

// Base URL is configurable via VITE_API_URL (e.g. in .env.local); defaults to the
// local FastAPI dev server.
const baseURL = import.meta.env?.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export default apiClient;
