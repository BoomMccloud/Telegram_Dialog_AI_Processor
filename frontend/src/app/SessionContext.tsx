'use client';

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';

type SessionStatus = 'authenticated' | 'pending' | 'error' | 'unauthenticated';

interface SessionContextType {
  sessionId: string | null;
  status: SessionStatus;
  isAuthenticated: boolean;
  login: (sessionId: string, initialStatus?: SessionStatus) => void;
  logout: () => void;
  refreshSession: () => Promise<boolean>;
  getSessionHeaders: () => HeadersInit;
  setManagedInterval: (callback: () => void, delay: number) => number;
  managedFetch: (url: string, options?: RequestInit) => Promise<Response | null>;
}

// Create the context with a default undefined value
const SessionContext = createContext<SessionContextType | undefined>(undefined);

// Key used for storing the session ID in localStorage
const SESSION_KEY = 'sessionId';

// API URL from environment
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
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
  const login = useCallback((newSessionId: string, initialStatus?: SessionStatus) => {
    // Clear any existing intervals before setting the new session
    clearAllIntervals();
    
    localStorage.setItem(SESSION_KEY, newSessionId);
    setSessionId(newSessionId);
    
    if (initialStatus) {
      setStatus(initialStatus);
      return;
    }
    
    // Check the session status
    fetch(`${API_URL}/auth/session/${newSessionId}`)
      .then(response => response.json())
      .then(data => {
        setStatus(data.status);
        console.log('Session login successful:', newSessionId, 'status:', data.status);
        
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
    
    // If we have a session ID, call the logout endpoint
    if (sessionId) {
      try {
        // Call the explicit logout endpoint first
        const response = await fetch(`${API_URL}/auth/logout/${sessionId}`, {
          method: 'POST',
          headers: {
            'X-Session-ID': sessionId
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
    setSessionId(null);
    setStatus('unauthenticated');
    
    // Navigate to login page
    router.push('/');
    
    console.log('Session logged out');
  }, [clearAllIntervals, router, sessionId]);

  // Load session from localStorage on mount
  useEffect(() => {
    const loadStoredSession = async () => {
      const storedSessionId = localStorage.getItem(SESSION_KEY);
      
      if (storedSessionId) {
        // Don't set the session ID until we verify it's valid
        try {
          const response = await fetch(`${API_URL}/auth/session/${storedSessionId}`);
          
          if (response.ok) {
            const data = await response.json();
            if (data.status === 'authenticated') {
              setSessionId(storedSessionId);
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
    if (!sessionId) {
      console.error('Attempting fetch without a valid session ID');
      return null;
    }
    
    const controller = new AbortController();
    const signal = controller.signal;
    
    activeRequests.current.push(controller);
    
    try {
      // Ensure headers are properly merged with session ID
      const headers = {
        ...options.headers,
        'X-Session-ID': sessionId
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
  }, [sessionId, logout]);

  // Refresh the session - returns true if successful
  const refreshSession = useCallback(async (): Promise<boolean> => {
    if (!sessionId) return false;
    
    try {
      const controller = new AbortController();
      activeRequests.current.push(controller);
      
      const response = await fetch(`${API_URL}/auth/session/${sessionId}/refresh`, {
        method: 'POST',
        signal: controller.signal
      });
      
      const index = activeRequests.current.indexOf(controller);
      if (index > -1) {
        activeRequests.current.splice(index, 1);
      }
      
      if (response.ok) {
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
  }, [sessionId, logout]);

  // Get headers with the session ID
  const getSessionHeaders = useCallback((): HeadersInit => {
    return {
      'Content-Type': 'application/json',
      'X-Session-ID': sessionId || ''
    };
  }, [sessionId]);

  // Context value
  const value = {
    sessionId,
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