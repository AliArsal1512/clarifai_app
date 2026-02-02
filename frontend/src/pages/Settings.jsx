import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Settings.css';

const Settings = () => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleDeleteAccount = async (e) => {
    e.preventDefault();
    setError('');

    if (!password) {
      setError('Please enter your password');
      return;
    }

    if (!window.confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
      return;
    }

    try {
      const formData = new FormData();
      formData.append('password', password);

      const response = await fetch('/delete-account', {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });

      const data = await response.json();
      
      if (response.ok && data.success) {
        navigate('/');
        window.location.reload();
      } else {
        setError(data.error || 'Incorrect password or error deleting account');
      }
    } catch (error) {
      setError('An error occurred. Please try again.');
    }
  };

  return (
    <div className="container-fluid settings-section" style={{ maxWidth: '1400px', width: '100%' }}>
      <section className="settings-section" style={{ paddingTop: '80px' }}>
        <div className="welcome-text mb-4">
          <h2>Settings</h2>
        </div>

        <div className="card">
          <div className="card-header-red bg-danger text-white">
            <h5 className="mb-0">Delete Account</h5>
          </div>
          <div className="card-body">
            <p className="text-muted">This action cannot be undone. This will permanently delete your account and all your submissions.</p>
            {error && <div className="alert alert-danger">{error}</div>}
            <form onSubmit={handleDeleteAccount}>
              <div className="mb-3">
                <label htmlFor="password" className="form-label">Enter your password to confirm</label>
                <input
                  type="password"
                  className="form-control"
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
              <button type="submit" className="btn btn-danger">
                Delete Account
              </button>
            </form>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Settings;

