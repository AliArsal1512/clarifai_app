import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import './Navbar.css';
import config from '../config';

const Navbar = ({ isAuthenticated, user, onLogout }) => {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const [isNavCollapsed, setIsNavCollapsed] = useState(true);

  const handleNavToggle = () => {
    setIsNavCollapsed(!isNavCollapsed);
  };

  const handleLogout = async () => {
    try {
      await fetch(`${config.apiBaseUrl}/auth/logout`, {
        method: 'GET',
        credentials: 'include',
      });
      onLogout();
      navigate('/');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const closeNavbar = () => {
    setIsNavCollapsed(true);
  };

  return (
    <nav id="mainNavbar" className="navbar navbar-expand-lg fixed-top">
      <div className="container-fluid" style={{ maxWidth: '1400px', width: '100%' }}>
        <Link className="navbar-brand" to="/" onClick={closeNavbar}>
          ClarifAI
        </Link>
        <button
          className="navbar-toggler"
          type="button"
          onClick={handleNavToggle}
          aria-expanded={!isNavCollapsed}
          aria-label="Toggle navigation"
        >
          <span className="navbar-toggler-icon"></span>
        </button>
        <div className={`collapse navbar-collapse ${!isNavCollapsed ? 'show' : ''}`} id="navbarNav">
          <ul className="navbar-nav ms-auto">
            <li className="nav-item">
              <Link className="nav-link" to="/" onClick={closeNavbar}>
                Home
              </Link>
            </li>
            {isAuthenticated ? (
              <>
                <li className="nav-item">
                  <Link className="nav-link" to="/model" onClick={closeNavbar}>
                    Model
                  </Link>
                </li>
                <li className="nav-item">
                  <Link className="nav-link" to="/dashboard" onClick={closeNavbar}>
                    Dashboard
                  </Link>
                </li>
                <li className="nav-item">
                  <Link className="nav-link" to="/settings" onClick={closeNavbar}>
                    Settings
                  </Link>
                </li>
                <li className="nav-item">
                  <button className="nav-link btn btn-link" onClick={() => {
                    handleLogout();
                    closeNavbar();
                  }}>
                    Logout
                  </button>
                </li>
              </>
            ) : (
              <>
                <li className="nav-item">
                  <Link className="nav-link" to="/auth/login" onClick={closeNavbar}>
                    Login
                  </Link>
                </li>
                <li className="nav-item">
                  <Link className="nav-link" to="/auth/signup" onClick={closeNavbar}>
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