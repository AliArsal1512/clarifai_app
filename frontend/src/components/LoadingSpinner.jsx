// components/LoadingSpinner.jsx
import React from 'react';
import './LoadingSpinner.css';

const LoadingSpinner = () => {
  return (
    <div className="loading-spinner-container">
      <div className="loading-spinner-icon">⏳</div>
      <p className="loading-text">waking up backend on render, please visit <a href="https://clarifai-app.onrender.com" target="_blank" rel="noopener noreferrer">https://clarifai-app.onrender.com</a> to see progress</p>
    </div>
  );
};

export default LoadingSpinner;