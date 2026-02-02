import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import './Navbar.css';

const Navbar = ({ isAuthenticated, user, onLogout }) => {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();

  const handleLogout = async () => {
    try {
      await fetch('/auth/logout', {
        method: 'GET',
        credentials: 'include',
      });
      onLogout();
      navigate('/');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <nav id="mainNavbar" className="navbar navbar-expand-lg fixed-top">
      <div className="container-fluid" style={{ maxWidth: '1400px', width: '100%' }}>
        <Link className="navbar-brand" to="/">
          ClarifAI
        </Link>
        <button
          className="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#navbarNav"
          aria-controls="navbarNav"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span className="navbar-toggler-icon"></span>
        </button>
        <div className="collapse navbar-collapse" id="navbarNav">
          <ul className="navbar-nav ms-auto">
            <li className="nav-item">
              <Link className="nav-link" to="/">
                Home
              </Link>
            </li>
            {isAuthenticated ? (
              <>
                <li className="nav-item">
                  <Link className="nav-link" to="/model">
                    Model
                  </Link>
                </li>
                <li className="nav-item">
                  <Link className="nav-link" to="/dashboard">
                    Dashboard
                  </Link>
                </li>
                <li className="nav-item">
                  <Link className="nav-link" to="/settings">
                    Settings
                  </Link>
                </li>
                <li className="nav-item">
                  <button className="nav-link btn btn-link" onClick={handleLogout}>
                    Logout
                  </button>
                </li>
              </>
            ) : (
              <>
                <li className="nav-item">
                  <Link className="nav-link" to="/auth/login">
                    Login
                  </Link>
                </li>
                <li className="nav-item">
                  <Link className="nav-link" to="/auth/signup">
                    Sign Up
                  </Link>
                </li>
              </>
            )}
            <li className="nav-item">
              <button className="theme-toggle" onClick={toggleTheme}>
                <span className="theme-toggle-icon">{theme === 'light' ? '🌙' : '☀️'}</span>
              </button>
            </li>
          </ul>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;

