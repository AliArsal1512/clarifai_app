import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './Auth.css';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const result = await login(username, password);
    
    if (result.success) {
      navigate('/dashboard');
    } else {
      setError(result.error || 'Invalid username or password');
    }
  };

  return (
    <div className="login-page">
      <div className="log-sign-card card">
        <div className="card-body p-4">
          <p className="text-muted">
            For demo purposes, you can use the following credentials:
            <br />
            Username: <code>ali123</code>
            <br />
            Password: <code>ali123</code>
          </p>
          <h2 className="login-label text-center mb-4">Login</h2>
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
              Login
            </button>
          </form>
          <p className="mt-3 text-center">
            Don't have an account? <Link to="/auth/signup">Sign up</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;