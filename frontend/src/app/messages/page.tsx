'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from '../ThemeContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

interface Dialog {
  id: number;
  name: string;
  unread_count: number;
  is_group: boolean;
  is_channel: boolean;
  is_user: boolean;
  last_message?: {
    id: string;
    text: string;
    sender: {
      id: string;
      name: string;
    };
    date: string;
  };
}

interface ProcessingStatus {
  isProcessing: boolean;
  error: string | null;
  lastProcessed: number[];
}

type TabType = 'groups' | 'channels' | 'direct';

interface DialogListProps {
  dialogs: Dialog[];
  selectedDialogs: Set<number>;
  onToggleSelect: (dialogId: number) => void;
}

const DialogList: React.FC<DialogListProps> = ({ dialogs, selectedDialogs, onToggleSelect }) => {
  if (dialogs.length === 0) {
    return (
      <div className="text-center text-gray-500 dark:text-gray-400 py-4">
        No chats found
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {dialogs.map((dialog) => (
        <div
          key={dialog.id}
          className={`
            p-4 rounded-lg shadow bg-white dark:bg-gray-800 
            hover:bg-gray-50 dark:hover:bg-gray-700 
            cursor-pointer transition-colors border border-gray-200 dark:border-gray-700
            flex justify-between items-center
            ${selectedDialogs.has(dialog.id) ? 'ring-2 ring-blue-500 dark:ring-blue-400' : ''}
          `}
          onClick={() => onToggleSelect(dialog.id)}
        >
          <div className="flex items-center flex-1">
            <input
              type="checkbox"
              checked={selectedDialogs.has(dialog.id)}
              onChange={() => onToggleSelect(dialog.id)}
              className="h-4 w-4 text-blue-600 rounded border-gray-300 
                focus:ring-blue-500 dark:border-gray-600 dark:focus:ring-blue-400
                mr-4"
              onClick={(e) => e.stopPropagation()}
            />
            <h2 className="font-semibold text-lg dark:text-white truncate pr-4">
              {dialog.name}
            </h2>
          </div>
          <div className={`
            flex items-center whitespace-nowrap px-3 py-1 rounded-full text-sm
            ${dialog.unread_count > 0
              ? 'bg-blue-500 dark:bg-blue-600 text-white'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
            }`}
          >
            <span className="font-medium">{dialog.unread_count || '0'}</span>
            <span className="ml-1 font-normal">messages unread</span>
          </div>
        </div>
      ))}
    </div>
  );
};

const SelectionControls: React.FC<{
  dialogs: Dialog[];
  selectedDialogs: Set<number>;
  onSelectAll: () => void;
  onSelectUnread: () => void;
  onClearSelection: () => void;
  onProcessSelected: () => void;
  processingStatus: ProcessingStatus;
}> = ({ dialogs, selectedDialogs, onSelectAll, onSelectUnread, onClearSelection, onProcessSelected, processingStatus }) => {
  const selectedCount = selectedDialogs.size;
  const totalCount = dialogs.length;
  const unreadCount = dialogs.filter(d => d.unread_count > 0).length;

  return (
    <div className="mb-4 flex flex-col gap-3 bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
      <div className="flex flex-wrap gap-3 items-center">
        <div className="text-sm text-gray-600 dark:text-gray-300">
          Selected: {selectedCount} of {totalCount}
        </div>
        <div className="flex-1"></div>
        <button
          onClick={onSelectUnread}
          className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-200 
            bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 
            dark:hover:bg-gray-600 transition-colors"
        >
          Select Unread ({unreadCount})
        </button>
        <button
          onClick={onSelectAll}
          className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-200 
            bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 
            dark:hover:bg-gray-600 transition-colors"
        >
          Select All
        </button>
        <button
          onClick={onClearSelection}
          className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-200 
            bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 
            dark:hover:bg-gray-600 transition-colors"
        >
          Clear Selection
        </button>
        <button
          onClick={onProcessSelected}
          disabled={selectedCount === 0 || processingStatus.isProcessing}
          className={`
            px-4 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-2
            ${selectedCount > 0 && !processingStatus.isProcessing
              ? 'bg-blue-500 dark:bg-blue-600 text-white hover:bg-blue-600 dark:hover:bg-blue-700 cursor-pointer'
              : 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'}
          `}
        >
          {processingStatus.isProcessing ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
              Processing...
            </>
          ) : (
            'Process Selected'
          )}
        </button>
      </div>
      
      {processingStatus.error && (
        <div className="text-sm text-red-500 dark:text-red-400">
          Error: {processingStatus.error}
        </div>
      )}
      
      {processingStatus.lastProcessed.length > 0 && !processingStatus.error && (
        <div className="text-sm text-green-600 dark:text-green-400">
          Successfully queued {processingStatus.lastProcessed.length} chats for processing
        </div>
      )}
    </div>
  );
};

const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  
  return (
    <button
      onClick={toggleTheme}
      className="fixed top-4 right-4 p-2 rounded-lg bg-gray-200 dark:bg-gray-700 
        hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
      aria-label="Toggle theme"
    >
      {theme === 'light' ? (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
            d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      ) : (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
            d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707" />
        </svg>
      )}
    </button>
  );
};

// Interface for API response dialog format
interface ApiDialog {
  id: string;
  name: string;
  type: string;
  unread_count: number;
  last_message?: {
    id: string;
    text: string;
    sender: {
      id: string;
      name: string;
    };
    date: string;
  };
}

export default function MessagesPage() {
  const [dialogs, setDialogs] = useState<Dialog[]>([]);
  const [activeTab, setActiveTab] = useState<TabType>('direct');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDialogs, setSelectedDialogs] = useState<Set<number>>(new Set());
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus>({
    isProcessing: false,
    error: null,
    lastProcessed: []
  });
  const router = useRouter();
  
  // Get session ID from localStorage
  const sessionId = typeof window !== 'undefined' ? localStorage.getItem('sessionId') : null;

  // Load selected dialogs from localStorage
  useEffect(() => {
    const savedSelection = localStorage.getItem('selectedDialogs');
    if (savedSelection) {
      setSelectedDialogs(new Set(JSON.parse(savedSelection)));
    }
  }, []);

  // Save selected dialogs to localStorage
  useEffect(() => {
    localStorage.setItem('selectedDialogs', JSON.stringify(Array.from(selectedDialogs)));
  }, [selectedDialogs]);

  useEffect(() => {
    // Redirect to login if no session ID
    if (!sessionId) {
      router.push('/');
      return;
    }

    const fetchDialogs = async () => {
      try {
        console.log(`Fetching dialogs from: ${API_URL}/dialogs/${sessionId}`);
        const response = await fetch(`${API_URL}/dialogs/${sessionId}`);
        console.log('Response status:', response.status);
        
        // Log the response content type
        console.log('Content-Type:', response.headers.get('content-type'));
        
        if (!response.ok) {
          const responseText = await response.text();
          console.error('Error response text:', responseText);
          throw new Error(`Failed to fetch dialogs: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Dialogs data:', data);
        
        // Transform the API data to match the Dialog interface
        if (data && Array.isArray(data.dialogs)) {
          const transformedDialogs = data.dialogs.map((dialog: ApiDialog) => ({
            id: parseInt(dialog.id, 10), // Convert string ID to number
            name: dialog.name,
            unread_count: dialog.unread_count,
            is_group: dialog.type === 'group',
            is_channel: dialog.type === 'channel',
            is_user: dialog.type === 'private',
            last_message: dialog.last_message
          }));
          console.log('Transformed dialogs:', transformedDialogs);
          setDialogs(transformedDialogs);
        } else {
          console.error('Unexpected response format:', data);
          setError('Received invalid data format from server');
        }
      } catch (err) {
        console.error('Fetch error details:', err);
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchDialogs();
    // Refresh dialogs every 30 seconds
    const interval = setInterval(fetchDialogs, 30000);
    return () => clearInterval(interval);
  }, [sessionId, router]);

  const handleToggleSelect = (dialogId: number) => {
    setSelectedDialogs(prev => {
      const newSelection = new Set(prev);
      if (newSelection.has(dialogId)) {
        newSelection.delete(dialogId);
      } else {
        newSelection.add(dialogId);
      }
      return newSelection;
    });
  };

  const handleSelectAll = () => {
    const currentDialogs = filteredDialogs[activeTab];
    setSelectedDialogs(new Set(currentDialogs.map(d => d.id)));
  };

  const handleSelectUnread = () => {
    const currentDialogs = filteredDialogs[activeTab];
    setSelectedDialogs(new Set(currentDialogs.filter(d => d.unread_count > 0).map(d => d.id)));
  };

  const handleClearSelection = () => {
    setSelectedDialogs(new Set());
  };

  const handleProcessSelected = async () => {
    if (selectedDialogs.size === 0 || processingStatus.isProcessing) return;

    setProcessingStatus(prev => ({
      ...prev,
      isProcessing: true,
      error: null
    }));

    try {
      // Process each selected dialog individually
      const selectPromises = Array.from(selectedDialogs).map(dialogId => {
        // Find the dialog object to get the name
        const dialog = dialogs.find(d => d.id === dialogId);
        if (!dialog) {
          throw new Error(`Dialog with ID ${dialogId} not found`);
        }
        
        return fetch(`${API_URL}/dialogs/${sessionId}/select`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            dialog_id: dialogId,
            dialog_name: dialog.name, // Include the dialog name
            processing_enabled: true, // Match the backend field name
            priority: 1, // Default priority
          }),
        });
      });
      
      // Wait for all selections to complete
      const results = await Promise.all(selectPromises);
      
      // Check if any requests failed
      const failedRequests = results.filter(response => !response.ok);
      if (failedRequests.length > 0) {
        throw new Error(`Failed to select ${failedRequests.length} dialogs`);
      }

      // Save processed dialogs to localStorage
      const processedDialogs = new Set(
        JSON.parse(localStorage.getItem('processedDialogs') || '[]')
      );
      selectedDialogs.forEach(id => processedDialogs.add(id));
      localStorage.setItem('processedDialogs', JSON.stringify(Array.from(processedDialogs)));

      setProcessingStatus(prev => ({
        ...prev,
        isProcessing: false,
        error: null,
        lastProcessed: Array.from(selectedDialogs)
      }));

      // Clear selection after successful processing
      setSelectedDialogs(new Set());
    } catch (err) {
      setProcessingStatus(prev => ({
        ...prev,
        isProcessing: false,
        error: err instanceof Error ? err.message : 'An error occurred while processing'
      }));
    }
  };

  if (!sessionId) {
    return null; // Will redirect
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center dark:bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-white"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center dark:bg-gray-900">
        <div className="text-red-500 dark:text-red-400">Error: {error}</div>
      </div>
    );
  }

  const filteredDialogs = {
    groups: dialogs.filter(d => d.is_group),
    channels: dialogs.filter(d => d.is_channel),
    direct: dialogs.filter(d => d.is_user)
  };

  const totalUnread = {
    groups: filteredDialogs.groups.reduce((sum, d) => sum + d.unread_count, 0),
    channels: filteredDialogs.channels.reduce((sum, d) => sum + d.unread_count, 0),
    direct: filteredDialogs.direct.reduce((sum, d) => sum + d.unread_count, 0)
  };

  return (
    <main className="flex min-h-screen flex-col p-8 bg-gray-50 dark:bg-gray-900">
      <ThemeToggle />
      
      <h1 className="text-3xl font-bold mb-6 text-gray-900 dark:text-white">
        Your Chats
      </h1>
      
      <div className="mb-6">
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="-mb-px flex space-x-8" aria-label="Tabs">
            {[
              { id: 'direct', name: 'Direct Messages', count: totalUnread.direct },
              { id: 'groups', name: 'Groups', count: totalUnread.groups },
              { id: 'channels', name: 'Channels', count: totalUnread.channels },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`
                  whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm
                  ${activeTab === tab.id
                    ? 'border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300 dark:hover:border-gray-600'
                  }
                `}
              >
                {tab.name}
                {tab.count > 0 && (
                  <span className={`
                    ml-2 py-0.5 px-2 rounded-full text-xs
                    ${activeTab === tab.id 
                      ? 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400' 
                      : 'bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-300'}
                  `}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>
      </div>

      <SelectionControls
        dialogs={filteredDialogs[activeTab]}
        selectedDialogs={selectedDialogs}
        onSelectAll={handleSelectAll}
        onSelectUnread={handleSelectUnread}
        onClearSelection={handleClearSelection}
        onProcessSelected={handleProcessSelected}
        processingStatus={processingStatus}
      />

      <div className="mt-4">
        <DialogList 
          dialogs={filteredDialogs[activeTab]}
          selectedDialogs={selectedDialogs}
          onToggleSelect={handleToggleSelect}
        />
      </div>
    </main>
  );
} 