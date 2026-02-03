// src/config.js
const config = {
  apiBaseUrl: window.location.hostname === 'localhost' 
    ? 'http://localhost:3000/api'  // Local development
    : '/api',  // Production (will work with Flask on same domain)
};

export default config;