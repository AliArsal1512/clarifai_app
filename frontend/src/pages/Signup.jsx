import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './Auth.css';

const Signup = ({ onSignup }) => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const formData = new FormData();
      formData.append('username', username.trim());
      formData.append('email', email.trim());
      formData.append('password', password);

      const response = await fetch('/auth/signup', {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });

      const data = await response.json();
      
      if (response.ok && data.success) {
        onSignup();
        navigate(data.redirect || '/dashboard');
      } else {
        setError(data.error || 'Registration failed. Please try again.');
      }
    } catch (error) {
      setError('An error occurred. Please try again.');
    }
  };

  return (
    <div className="signup-page">
      <div className="log-sign-card card">
        <div className="card-body p-4">
          <h2 className="login-label text-center mb-4">Sign Up</h2>
          {error && <div className="alert alert-danger">{error}</div>}
          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label htmlFor="username" className="form-label">Username</label>
              <input
                type="text"
                className="form-control"
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div className="mb-3">
              <label htmlFor="email" className="form-label">Email</label>
              <input
                type="email"
                className="form-control"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="mb-3">
              <label htmlFor="password" className="form-label">Password</label>
              <input
                type="password"
                className="form-control"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <button type="submit" className="btn btn-primary clarifai-btn w-100">
              Sign Up
            </button>
          </form>
          <p className="mt-3 text-center">
            Already have an account? <Link to="/auth/login">Login</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Signup;

