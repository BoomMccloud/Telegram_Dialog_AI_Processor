'use client';

import { useState, useEffect } from 'react';
import { useSession } from '../SessionContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export default function DevTools() {
  const [isVisible, setIsVisible] = useState(false);
  const [mockSessionId, setMockSessionId] = useState('');
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const { sessionId, login, logout } = useSession();
  
  // Only show in development mode
  useEffect(() => {
    setIsVisible(process.env.NODE_ENV === 'development');
  }, []);

  if (!isVisible) {
    return null;
  }

  const setMockSession = () => {
    if (mockSessionId && mockSessionId.trim() !== '') {
      login(mockSessionId);
    }
  };

  const clearSession = () => {
    logout();
  };

  const copyToClipboard = () => {
    if (sessionId) {
      navigator.clipboard.writeText(sessionId);
      alert('Session ID copied to clipboard!');
    }
  };

  const testApi = async () => {
    try {
      const response = await fetch('/api/health');
      const data = await response.json();
      alert(`API Test Result: ${JSON.stringify(data)}`);
    } catch (e) {
      alert(`API Test Error: ${e}`);
    }
  };

  const authenticateSession = async () => {
    if (!sessionId) {
      alert('No active session to authenticate');
      return;
    }

    setIsAuthenticating(true);
    try {
      // Call the force-session/authenticate endpoint to authenticate the current session
      const response = await fetch(`${API_URL}/auth/force-session/${sessionId}/authenticate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(error);
      }

      const data = await response.json();
      if (data.status === 'success') {
        alert('Session authenticated successfully!');
        // Re-login with the same session ID to refresh the frontend state
        login(sessionId);
      } else {
        throw new Error('Failed to authenticate session');
      }
    } catch (error) {
      console.error('Error authenticating session:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      alert(`Failed to authenticate session: ${errorMessage}`);
    } finally {
      setIsAuthenticating(false);
    }
  };

  return (
    <div className="fixed bottom-4 right-4 p-4 bg-gray-800 text-white rounded-lg shadow-lg z-50 text-sm">
      <h3 className="font-bold text-yellow-300 mb-2">Dev Tools</h3>
      <div className="mb-2">
        <div className="text-xs text-gray-400">Current Session:</div>
        <div className="font-mono text-xs break-all max-w-xs">{sessionId || '(none)'}</div>
      </div>
      
      <div className="flex flex-col space-y-2 mt-3">
        <input
          type="text"
          value={mockSessionId}
          onChange={(e) => setMockSessionId(e.target.value)}
          placeholder="Enter mock session ID"
          className="px-2 py-1 text-black text-sm rounded"
        />
        
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={setMockSession}
            className="bg-blue-600 hover:bg-blue-700 px-2 py-1 rounded text-xs"
          >
            Set Session
          </button>
          
          <button
            onClick={clearSession}
            className="bg-red-600 hover:bg-red-700 px-2 py-1 rounded text-xs"
          >
            Clear Session
          </button>
          
          <button
            onClick={copyToClipboard}
            className="bg-gray-600 hover:bg-gray-700 px-2 py-1 rounded text-xs"
            disabled={!sessionId}
          >
            Copy ID
          </button>
          
          <button
            onClick={testApi}
            className="bg-green-600 hover:bg-green-700 px-2 py-1 rounded text-xs"
          >
            Test API
          </button>

          <button
            onClick={authenticateSession}
            disabled={!sessionId || isAuthenticating}
            className={`col-span-2 ${
              isAuthenticating 
                ? 'bg-yellow-600 cursor-wait' 
                : 'bg-purple-600 hover:bg-purple-700'
            } px-2 py-1 rounded text-xs`}
          >
            {isAuthenticating ? 'Authenticating...' : 'Authenticate Session'}
          </button>
        </div>
      </div>
    </div>
  );
}

