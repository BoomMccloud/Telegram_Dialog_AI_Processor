'use client';

import { useState, useEffect } from 'react';
import { useSession } from '../SessionContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export default function DevTools() {
  const [isVisible, setIsVisible] = useState(false);
  const [mockToken, setMockToken] = useState('');
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const { token, login, logout } = useSession();
  
  // Only show in development mode
  useEffect(() => {
    setIsVisible(process.env.NODE_ENV === 'development');
  }, []);

  if (!isVisible) {
    return null;
  }

  const setMockSession = () => {
    if (mockToken && mockToken.trim() !== '') {
      login(mockToken);
    }
  };

  const clearSession = () => {
    logout();
  };

  const copyToClipboard = () => {
    if (token) {
      navigator.clipboard.writeText(token);
      alert('JWT token copied to clipboard!');
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
    if (!token) {
      alert('No active session to authenticate');
      return;
    }

    setIsAuthenticating(true);
    try {
      // Call the force-authenticate endpoint to authenticate the current session
      const response = await fetch(`${API_URL}/auth/force-authenticate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(error);
      }

      const data = await response.json();
      if (data.status === 'success') {
        alert('Session authenticated successfully!');
        // Re-login with the same token to refresh the frontend state
        login(token);
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
    <div className="fixed bottom-4 right-4 p-4 bg-gray-800 text-white rounded-lg shadow-lg">
      <h3 className="text-lg font-bold mb-4">Development Tools</h3>
      
      <div className="space-y-4">
        <div>
          <label className="block mb-2">Mock JWT Token:</label>
          <input
            type="text"
            value={mockToken}
            onChange={(e) => setMockToken(e.target.value)}
            className="w-full p-2 text-black rounded"
            placeholder="Enter JWT token"
          />
          <button
            onClick={setMockSession}
            className="mt-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Set Mock Session
          </button>
        </div>

        <div className="space-y-2">
          <button
            onClick={clearSession}
            className="w-full px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
          >
            Clear Session
          </button>
          
          <button
            onClick={copyToClipboard}
            className="w-full px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
            disabled={!token}
          >
            Copy JWT Token
          </button>
          
          <button
            onClick={authenticateSession}
            className="w-full px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600"
            disabled={!token || isAuthenticating}
          >
            {isAuthenticating ? 'Authenticating...' : 'Force Authenticate'}
          </button>
          
          <button
            onClick={testApi}
            className="w-full px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600"
          >
            Test API
          </button>
        </div>

        <div className="mt-4 text-sm">
          <p>Current Token:</p>
          <pre className="mt-1 p-2 bg-gray-700 rounded overflow-x-auto">
            {token || 'No token'}
          </pre>
        </div>
      </div>
    </div>
  );
}

