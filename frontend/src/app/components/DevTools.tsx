'use client';

import { useState, useEffect } from 'react';
import { useSession } from '../SessionContext';

export default function DevTools() {
  const [isVisible, setIsVisible] = useState(false);
  const [mockSessionId, setMockSessionId] = useState('');
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
        </div>
      </div>
    </div>
  );
}

