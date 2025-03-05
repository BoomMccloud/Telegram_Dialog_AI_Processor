'use client';

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';

type SessionStatus = 'authenticated' | 'pending' | 'error' | 'unauthenticated';

interface SessionContextType {
  token: string | null;
  status: SessionStatus;
  isAuthenticated: boolean;
  login: (token: string, initialStatus?: SessionStatus) => void;
  logout: () => void;
  refreshSession: () => Promise<boolean>;
  getSessionHeaders: () => HeadersInit;
  setManagedInterval: (callback: () => void, delay: number) => number;
  managedFetch: (url: string, options?: RequestInit) => Promise<Response | null>;
}

// Create the context with a default undefined value
const SessionContext = createContext<SessionContextType | undefined>(undefined);

// Key used for storing the session ID in localStorage
const SESSION_KEY = 'jwt_token';

// API URL from environment
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [status, setStatus] = useState<SessionStatus>('unauthenticated');
  const router = useRouter();
  
  // Store active intervals for cleanup
  const activeIntervals = useRef<number[]>([]);
  const activeRequests = useRef<AbortController[]>([]);

  // Clear all active intervals
  const clearAllIntervals = useCallback(() => {
    activeIntervals.current.forEach(interval => {
      clearInterval(interval);
    });
    activeIntervals.current = [];
    
    // Abort any in-flight requests
    activeRequests.current.forEach(controller => {
      controller.abort();
    });
    activeRequests.current = [];
  }, []);
  
  // Set a new interval and track it
  const setManagedInterval = useCallback((callback: () => void, delay: number) => {
    const interval = window.setInterval(callback, delay) as unknown as number;
    activeIntervals.current.push(interval);
    return interval;
  }, []);

  // Login function
  const login = useCallback((newToken: string, initialStatus?: SessionStatus) => {
    // Clear any existing intervals before setting the new session
    clearAllIntervals();
    
    localStorage.setItem(SESSION_KEY, newToken);
    setToken(newToken);
    
    if (initialStatus) {
      setStatus(initialStatus);
      return;
    }
    
    // Check the session status
    fetch(`${API_URL}/auth/session/verify`, {
      headers: {
        'Authorization': `Bearer ${newToken}`
      }
    })
      .then(response => response.json())
      .then(data => {
        setStatus(data.status);
        console.log('Session login successful:', 'status:', data.status);
        
        // If authenticated and no initial status was provided, redirect to home
        if (data.status === 'authenticated' && !initialStatus) {
          router.push('/home');
        }
      })
      .catch(error => {
        console.error('Error checking session status:', error);
        setStatus('error');
      });
  }, [clearAllIntervals, router]);

  // Logout function
  const logout = useCallback(async () => {
    clearAllIntervals();
    
    // If we have a token, call the logout endpoint
    if (token) {
      try {
        // Call the explicit logout endpoint first
        const response = await fetch(`${API_URL}/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!response.ok) {
          console.error('Error during logout:', await response.text());
        }
      } catch (error) {
        console.error('Error during logout:', error);
      }
    }
    
    // Clear from localStorage
    localStorage.removeItem(SESSION_KEY);
    
    // Clear the session state
    setToken(null);
    setStatus('unauthenticated');
    
    // Navigate to login page
    router.push('/');
    
    console.log('Session logged out');
  }, [clearAllIntervals, router, token]);

  // Load session from localStorage on mount
  useEffect(() => {
    const loadStoredSession = async () => {
      const storedToken = localStorage.getItem(SESSION_KEY);
      
      if (storedToken) {
        // Don't set the token until we verify it's valid
        try {
          const response = await fetch(`${API_URL}/auth/session/verify`, {
            headers: {
              'Authorization': `Bearer ${storedToken}`
            }
          });
          
          if (response.ok) {
            const data = await response.json();
            if (data.status === 'authenticated') {
              setToken(storedToken);
              setStatus('authenticated');
            } else {
              // Session exists but is not authenticated
              await logout();
            }
          } else {
            // Session is invalid
            await logout();
          }
        } catch (error) {
          console.error('Error validating session:', error);
          setStatus('error');
          // Clean up invalid session
          await logout();
        }
      }
    };

    loadStoredSession();
    
    // Cleanup function
    return () => {
      clearAllIntervals();
    };
  }, [clearAllIntervals, logout]);

  // Create a managed fetch function that can be aborted when the session changes
  const managedFetch = useCallback(async (url: string, options: RequestInit = {}) => {
    if (!token) {
      console.error('Attempting fetch without a valid token');
      return null;
    }
    
    const controller = new AbortController();
    const signal = controller.signal;
    
    activeRequests.current.push(controller);
    
    try {
      // Ensure headers are properly merged with Authorization token
      const headers = {
        ...options.headers,
        'Authorization': `Bearer ${token}`
      };
      
      const response = await fetch(url, { 
        ...options, 
        headers,
        signal 
      });
      
      // Handle 401 (Unauthorized) by clearing the session
      if (response.status === 401) {
        console.error('Received 401 Unauthorized response, logging out:', url);
        logout();
        return null;
      }
      
      return response;
    } catch (error) {
      if ((error as Error).name !== 'AbortError') {
        console.error('Fetch error:', error);
      }
      return null;
    } finally {
      // Remove controller from active requests
      const index = activeRequests.current.indexOf(controller);
      if (index > -1) {
        activeRequests.current.splice(index, 1);
      }
    }
  }, [token, logout]);

  // Refresh the session - returns true if successful
  const refreshSession = useCallback(async (): Promise<boolean> => {
    if (!token) return false;
    
    try {
      const controller = new AbortController();
      activeRequests.current.push(controller);
      
      const response = await fetch(`${API_URL}/auth/session/refresh`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        signal: controller.signal
      });
      
      const index = activeRequests.current.indexOf(controller);
      if (index > -1) {
        activeRequests.current.splice(index, 1);
      }
      
      if (response.ok) {
        const data = await response.json();
        // Update token with new refreshed token
        if (data.token) {
          localStorage.setItem(SESSION_KEY, data.token);
          setToken(data.token);
        }
        console.log('Session refreshed successfully');
        return true;
      } else {
        console.error('Failed to refresh session');
        if (response.status === 401) {
          logout();
        }
        return false;
      }
    } catch (error) {
      console.error('Error refreshing session:', error);
      return false;
    }
  }, [token, logout]);

  // Get headers with the Authorization token
  const getSessionHeaders = useCallback((): HeadersInit => {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token || ''}`
    };
  }, [token]);

  // Context value
  const value = {
    token,
    status,
    isAuthenticated: status === 'authenticated',
    login,
    logout,
    refreshSession,
    getSessionHeaders,
    setManagedInterval,
    managedFetch
  };

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  );
}

// Custom hook to use the session context
export function useSession() {
  const context = useContext(SessionContext);
  if (context === undefined) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
} 