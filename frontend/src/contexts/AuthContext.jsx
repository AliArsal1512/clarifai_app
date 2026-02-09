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
        // Call backend logout
        await fetch(`${config.apiBaseUrl}/auth/logout`, {
        method: 'GET',
        credentials: 'include',
        });
        
        // Clear ALL cookies (optional aggressive approach)
        document.cookie.split(";").forEach((c) => {
        document.cookie = c
            .replace(/^ +/, "")
            .replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
        });
        
        // Clear local storage if you're using it
        localStorage.clear();
        sessionStorage.clear();
        
    } catch (error) {
        console.error('Logout failed:', error);
    } finally {
        // Always clear the user state
        setUser(null);
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