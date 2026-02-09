import { createContext, useState, useContext, useEffect } from 'react';
import config from '../config';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check auth status on mount
  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const response = await fetch(`${config.apiBaseUrl}/auth/check`, {
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.authenticated) {
          setUser(data.user);
        }
      }
    } catch (error) {
      console.error('Auth check failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    try {
      const formData = new FormData();
      formData.append('username', username);
      formData.append('password', password);

      const response = await fetch(`${config.apiBaseUrl}/auth/login`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });

      const data = await response.json();
      
      if (response.ok && data.success) {
        setUser(data.user || { username });
        return { success: true, data };
      } else {
        return { success: false, error: data.error || 'Login failed' };
      }
    } catch (error) {
      return { success: false, error: 'Network error' };
    }
  };

  const logout = async () => {
    try {
        // Call backend logout with POST method
        const response = await fetch(`${config.apiBaseUrl}/auth/logout`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            throw new Error('Logout failed');
        }

        // Clear frontend state IMMEDIATELY
        setUser(null);
        
    } catch (error) {
        console.error('Logout failed:', error);
        setUser(null);
    } finally {
        // Always clear storage and redirect, regardless of response
        localStorage.clear();
        sessionStorage.clear();
        
        // Give a small delay for cookie headers to be processed
        setTimeout(() => {
            window.location.href = '/';
        }, 100);
    }
  };

  const signup = async (userData) => {
    try {
        const formData = new FormData();
        Object.keys(userData).forEach(key => {
        formData.append(key, userData[key]);
        });

        const response = await fetch(`${config.apiBaseUrl}/auth/signup`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
        });

        const data = await response.json();
        
        if (response.ok && data.success) {
        return { success: true, data };
        } else {
        return { success: false, error: data.error || 'Registration failed' };
        }
    } catch (error) {
        return { success: false, error: 'Network error' };
    }
    };

  const value = {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    logout,
    signup,
    checkAuth,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};