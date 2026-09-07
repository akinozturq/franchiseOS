import axios from "axios";

const API_BASE_URL = "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json"
  }
});

// Request interceptor to attach JWT token and active branch
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("franchise_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const activeBranchId = localStorage.getItem("franchise_active_branch_id");
  if (activeBranchId) {
    config.headers["X-Branch-Id"] = activeBranchId;
  }
  return config;
});

// Response interceptor to handle 401
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem("franchise_token");
      localStorage.removeItem("franchise_user");
      window.dispatchEvent(new Event("auth-changed"));
    }
    return Promise.reject(error);
  }
);

export default apiClient;

