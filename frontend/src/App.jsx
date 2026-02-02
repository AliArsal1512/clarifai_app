import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import Model from './pages/Model';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Settings from './pages/Settings';
import './App.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    // Check if user is authenticated on mount
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      // Check authentication status via API
      const response = await fetch('/api/check-auth', {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setIsAuthenticated(data.authenticated);
        setUser(data.user);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
    }
  };

  return (
    <ThemeProvider>
      <Router>
        <div className="app">
          <Navbar isAuthenticated={isAuthenticated} user={user} onLogout={() => setIsAuthenticated(false)} />
          <Routes>
            <Route path="/" element={<Home />} />
            <Route 
              path="/model" 
              element={isAuthenticated ? <Model /> : <Navigate to="/auth/login" />} 
            />
            <Route 
              path="/dashboard" 
              element={isAuthenticated ? <Dashboard /> : <Navigate to="/auth/login" />} 
            />
            <Route 
              path="/settings" 
              element={isAuthenticated ? <Settings /> : <Navigate to="/auth/login" />} 
            />
            <Route 
              path="/auth/login" 
              element={<Login onLogin={() => { setIsAuthenticated(true); checkAuth(); }} />} 
            />
            <Route 
              path="/auth/signup" 
              element={<Signup onSignup={() => { setIsAuthenticated(true); checkAuth(); }} />} 
            />
          </Routes>
        </div>
      </Router>
    </ThemeProvider>
  );
}

export default App;

