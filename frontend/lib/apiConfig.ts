// lib/apiConfig.ts
export const API_CONFIG = {
  // Production URL
  production: 'https://ayishaalee-todo-app.hf.space',
  // Development URL
  development: 'http://localhost:8001',
  // Default fallback
  default: 'http://localhost:8001'
};

// Determine the base URL based on environment
export const getBaseURL = (): string => {
  if (typeof window !== 'undefined') {
    // Client-side
    return process.env.NEXT_PUBLIC_API_URL || 
           (process.env.NODE_ENV === 'production' ? API_CONFIG.production : API_CONFIG.development);
  } else {
    // Server-side
    return process.env.BACKEND_API_URL || 
           process.env.NEXT_PUBLIC_API_URL || 
           (process.env.NODE_ENV === 'production' ? API_CONFIG.production : API_CONFIG.development);
  }
};

export default getBaseURL;