import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Auth
export const register = (studentId, name, email) => 
  api.post('/api/auth/register', { student_id: studentId, name, email });

export const login = (studentId) => 
  api.post('/api/auth/login', { student_id: studentId });

export const logout = () => 
  api.post('/api/auth/logout');

export const getCurrentUser = () => 
  api.get('/api/auth/me');

// Videos
export const getNextVideo = () => 
  api.get('/api/videos/next');

export const claimVideo = (videoId, preset) => 
  api.post(`/api/videos/${videoId}/claim`, { preset });

export const startProcessing = (videoId) => 
  api.post(`/api/videos/${videoId}/processing`);

export const submitResults = (videoId, results) => 
  api.post(`/api/videos/${videoId}/results`, results);

export const submitReview = (videoId, review) => 
  api.post(`/api/videos/${videoId}/review`, review);

// Stats
export const getStudentStats = () => 
  api.get('/api/stats/student');

export const getOverallStats = () => 
  api.get('/api/stats/overall');

export const getDomainStats = () => 
  api.get('/api/stats/domains');

export default api;