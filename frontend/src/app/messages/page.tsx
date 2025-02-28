'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import AppLayout from '../AppLayout';
import { useSession } from '../SessionContext';

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

// Interface for selected dialogs from the API
interface SelectedDialog {
  selection_id: string;
  dialog_id: number;
  dialog_name: string;
  is_active: boolean;
  processing_enabled: boolean;
  auto_reply_enabled: boolean;
  response_approval_required: boolean;
  priority: number;
  created_at: string;
  updated_at: string;
}

interface ProcessingStatus {
  isProcessing: boolean;
  error: string | null;
  lastProcessed: number[];
  lastUnprocessed: boolean;
}

// Update TabType to include 'selected'
type TabType = 'groups' | 'channels' | 'direct' | 'selected';

interface DialogListProps {
  dialogs: Dialog[];
  selectedDialogs: Set<number>;
  onToggleSelect: (dialogId: number) => void;
  processedDialogs?: number[];
}

const DialogList: React.FC<DialogListProps> = ({ dialogs, selectedDialogs, onToggleSelect, processedDialogs = [] }) => {
  if (dialogs.length === 0) {
    return (
      <div className="text-center text-gray-500 dark:text-gray-400 py-4">
        No chats found
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {dialogs.map((dialog) => {
        const isProcessed = processedDialogs.includes(dialog.id);
        return (
          <div
            key={dialog.id}
            className={`
              p-4 rounded-lg shadow bg-white dark:bg-gray-800 
              hover:bg-gray-50 dark:hover:bg-gray-700 
              cursor-pointer transition-colors border border-gray-200 dark:border-gray-700
              flex justify-between items-center
              ${selectedDialogs.has(dialog.id) ? 'ring-2 ring-blue-500 dark:ring-blue-400' : ''}
              ${isProcessed ? 'border-l-4 border-l-green-500 dark:border-l-green-400' : ''}
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
              <div className="flex items-center flex-1">
                <h2 className="font-semibold text-lg dark:text-white truncate pr-2">
                  {dialog.name}
                </h2>
                {isProcessed && (
                  <span className="ml-2 px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100 rounded-full whitespace-nowrap">
                    Processing
                  </span>
                )}
              </div>
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
        );
      })}
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
  processedDialogs: number[];
}> = ({ 
  dialogs, 
  selectedDialogs, 
  onSelectAll, 
  onSelectUnread, 
  onClearSelection, 
  onProcessSelected, 
  processingStatus,
  processedDialogs 
}) => {
  const selectedCount = selectedDialogs.size;
  const totalCount = dialogs.length;
  const unreadCount = dialogs.filter(d => d.unread_count > 0).length;
  
  // Count how many selected dialogs are already being processed
  const selectedDialogsArr = Array.from(selectedDialogs);
  const alreadyProcessedCount = selectedDialogsArr.filter(id => processedDialogs.includes(id)).length;
  
  // Determine button state based on selection and processing status
  const allSelectedAreProcessed = alreadyProcessedCount === selectedCount && selectedCount > 0;
  const hasMixedSelection = alreadyProcessedCount > 0 && alreadyProcessedCount < selectedCount;
  
  // Button text changes based on selection state
  const buttonText = allSelectedAreProcessed 
    ? 'Stop Processing' 
    : 'Start Processing';
  
  // Button is disabled if: no selection, mixed selection, or currently processing
  const isButtonDisabled = 
    selectedCount === 0 || 
    hasMixedSelection || 
    processingStatus.isProcessing;

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
          disabled={isButtonDisabled}
          className={`
            px-4 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-2
            ${!isButtonDisabled && !processingStatus.isProcessing
              ? (allSelectedAreProcessed 
                  ? 'bg-red-500 dark:bg-red-600 text-white hover:bg-red-600 dark:hover:bg-red-700'
                  : 'bg-blue-500 dark:bg-blue-600 text-white hover:bg-blue-600 dark:hover:bg-blue-700') 
              : 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500'} 
            cursor-${isButtonDisabled ? 'not-allowed' : 'pointer'}
          `}
        >
          {processingStatus.isProcessing ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
              Processing...
            </>
          ) : (
            buttonText
          )}
        </button>
      </div>
      
      {hasMixedSelection && (
        <div className="text-sm text-amber-500 dark:text-amber-400">
          Mixed selection: Please select either all processed or all unprocessed dialogs.
        </div>
      )}
      
      {processingStatus.error && (
        <div className="text-sm text-red-500 dark:text-red-400">
          Error: {processingStatus.error}
        </div>
      )}
      
      {!processingStatus.error && (
        processingStatus.lastProcessed.length > 0 ? (
          <div className="text-sm text-green-600 dark:text-green-400">
            Successfully queued {processingStatus.lastProcessed.length} chats for processing
          </div>
        ) : processingStatus.lastUnprocessed && (
          <div className="text-sm text-green-600 dark:text-green-400">
            Successfully removed selected chats from processing
          </div>
        )
      )}
    </div>
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
  const [activeTab, setActiveTab] = useState<TabType>('selected');
  const [dialogsLoading, setDialogsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDialogs, setSelectedDialogs] = useState<Set<number>>(new Set());
  const [apiSelectedDialogs, setApiSelectedDialogs] = useState<Dialog[]>([]);
  const [loadingSelected, setLoadingSelected] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus>({
    isProcessing: false,
    error: null,
    lastProcessed: [],
    lastUnprocessed: false
  });
  const router = useRouter();
  const { sessionId, managedFetch, setManagedInterval } = useSession();

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
        const response = await managedFetch(`${API_URL}/dialogs/${sessionId}`);
        
        // If response is null (could happen if 401 was received and user was logged out)
        if (!response) {
          console.log('Null response received (possibly due to auth error)');
          setDialogsLoading(false);
          return;
        }
        
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
        setDialogsLoading(false);
      }
    };

    fetchDialogs();
    // Refresh dialogs every 30 seconds using the managed interval
    setManagedInterval(fetchDialogs, 30000);
  }, [sessionId, router, setManagedInterval]);

  // Function to fetch selected dialogs from the API
  const fetchSelectedDialogs = async () => {
    if (!sessionId) return;
    
    setLoadingSelected(true);
    try {
      console.log(`Fetching selected dialogs from: ${API_URL}/dialogs/${sessionId}/selected`);
      const response = await managedFetch(`${API_URL}/dialogs/${sessionId}/selected`);
      
      if (!response || !response.ok) {
        if (response) {
          const responseText = await response.text();
          console.error('Error response text:', responseText);
          throw new Error(`Failed to fetch selected dialogs: ${response.status} ${response.statusText}`);
        } else {
          throw new Error('Failed to fetch selected dialogs: No response received');
        }
      }
      
      const data = await response.json();
      console.log('Selected dialogs data:', data);
      
      // Transform the API data to match the Dialog interface
      if (data && Array.isArray(data)) {
        const transformedDialogs = data.map((dialog: SelectedDialog) => ({
          id: dialog.dialog_id,
          name: dialog.dialog_name,
          unread_count: 0, // Selected dialogs don't have unread count
          is_group: false, // We don't know the type from selected dialogs API
          is_channel: false,
          is_user: false,
          // Add selected-specific data
          processing_enabled: dialog.processing_enabled,
          auto_reply_enabled: dialog.auto_reply_enabled,
          priority: dialog.priority
        }));
        console.log('Transformed selected dialogs:', transformedDialogs);
        setApiSelectedDialogs(transformedDialogs);
      } else {
        console.error('Unexpected response format for selected dialogs:', data);
      }
    } catch (err) {
      console.error('Fetch selected dialogs error:', err);
      // Don't set the main error state, just log it
    } finally {
      setLoadingSelected(false);
    }
  };

  // Fetch selected dialogs whenever component mounts or session changes
  useEffect(() => {
    // Initially fetch selected dialogs when the component mounts
    if (sessionId) {
      fetchSelectedDialogs();
    }
  }, [sessionId]);

  // Fetch selected dialogs when switching to the selected tab to ensure fresh data
  useEffect(() => {
    if (activeTab === 'selected' && sessionId) {
      fetchSelectedDialogs();
    }
  }, [activeTab, sessionId]);

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

    // Get the list of processed dialogs
    const processedDialogsList = [
      ...processingStatus.lastProcessed,
      ...apiSelectedDialogs.map(d => d.id)
    ];
    
    // Check if all selected dialogs are already being processed
    const selectedDialogsArr = Array.from(selectedDialogs);
    const allSelectedAreProcessed = selectedDialogsArr.every(id => processedDialogsList.includes(id));
    
    setProcessingStatus(prev => ({
      ...prev,
      isProcessing: true,
      error: null
    }));

    try {
      if (allSelectedAreProcessed) {
        // Handle STOP PROCESSING - remove dialogs from processing
        const unprocessPromises = Array.from(selectedDialogs).map(dialogId => {
          // Find the dialog in apiSelectedDialogs to get the selection_id
          const selectedDialog = apiSelectedDialogs.find(d => d.id === dialogId);
          if (!selectedDialog) {
            throw new Error(`Dialog with ID ${dialogId} not found in selected dialogs`);
          }
          
          // Call the API to remove from processing using DELETE method
          return managedFetch(`${API_URL}/dialogs/${sessionId}/selected/${dialogId}`, {
            method: 'DELETE',
            headers: {
              'Content-Type': 'application/json',
            }
          });
        });
        
        // Wait for all unselections to complete
        const results = await Promise.all(unprocessPromises);
        
        // Check if any requests failed
        const failedRequests = results.filter(response => !response || !response.ok);
        if (failedRequests.length > 0) {
          throw new Error(`Failed to unselect ${failedRequests.length} dialogs`);
        }

        // Refresh the selected dialogs after unselecting
        await fetchSelectedDialogs();

        setProcessingStatus(prev => ({
          ...prev,
          isProcessing: false,
          error: null,
          lastProcessed: [],
          lastUnprocessed: true
        }));

      } else {
        // Handle START PROCESSING - original logic to add dialogs for processing
        const selectPromises = Array.from(selectedDialogs).map(dialogId => {
          // Find the dialog object to get the name
          const dialog = dialogs.find(d => d.id === dialogId);
          if (!dialog) {
            throw new Error(`Dialog with ID ${dialogId} not found`);
          }
          
          return managedFetch(`${API_URL}/dialogs/${sessionId}/select`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              dialog_id: dialogId,
              dialog_name: dialog.name,
              processing_enabled: true,
              priority: 1,
            }),
          });
        });
        
        // Wait for all selections to complete
        const results = await Promise.all(selectPromises);
        
        // Check if any requests failed
        const failedRequests = results.filter(response => !response || !response.ok);
        if (failedRequests.length > 0) {
          throw new Error(`Failed to select ${failedRequests.length} dialogs`);
        }

        setProcessingStatus(prev => ({
          ...prev,
          isProcessing: false,
          error: null,
          lastProcessed: Array.from(selectedDialogs),
          lastUnprocessed: false
        }));
      }

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

  if (dialogsLoading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-white"></div>
        </div>
      </AppLayout>
    );
  }

  if (error) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center">
          <div className="text-red-500 dark:text-red-400">Error: {error}</div>
        </div>
      </AppLayout>
    );
  }

  const filteredDialogs = {
    groups: dialogs.filter(d => d.is_group),
    channels: dialogs.filter(d => d.is_channel),
    direct: dialogs.filter(d => d.is_user),
    selected: apiSelectedDialogs
  };

  // Change to count dialogs instead of unread messages
  const totalDialogs = {
    groups: filteredDialogs.groups.length,
    channels: filteredDialogs.channels.length,
    direct: filteredDialogs.direct.length,
    selected: filteredDialogs.selected.length
  };

  return (
    <AppLayout>
      <div className="flex flex-col">
        <h1 className="text-3xl font-bold mb-6 text-gray-900 dark:text-white">
          Data Sources
        </h1>
        
        <div className="mb-6">
          <div className="border-b border-gray-200 dark:border-gray-700">
            <nav className="-mb-px flex space-x-8" aria-label="Tabs">
              {[
                { id: 'selected', name: 'Selected', count: totalDialogs.selected },
                { id: 'direct', name: 'Direct Messages', count: totalDialogs.direct },
                { id: 'groups', name: 'Groups', count: totalDialogs.groups },
                { id: 'channels', name: 'Channels', count: totalDialogs.channels },
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
                  <span className="ml-2 py-0.5 px-2 rounded-full text-xs font-normal
                    bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
                  >
                    {tab.count}
                  </span>
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Show loading indicator when switching to Selected tab */}
        {activeTab === 'selected' && loadingSelected && (
          <div className="flex justify-center my-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white"></div>
          </div>
        )}

        {/* Show existing selection controls */}
        <SelectionControls
          dialogs={filteredDialogs[activeTab]}
          selectedDialogs={selectedDialogs}
          onSelectAll={handleSelectAll}
          onSelectUnread={handleSelectUnread}
          onClearSelection={handleClearSelection}
          onProcessSelected={handleProcessSelected}
          processingStatus={processingStatus}
          processedDialogs={[
            ...processingStatus.lastProcessed,
            ...apiSelectedDialogs.map(d => d.id)
          ]}
        />
        
        {/* Show the dialog list filtered by the active tab */}
        <DialogList
          dialogs={filteredDialogs[activeTab]}
          selectedDialogs={selectedDialogs}
          onToggleSelect={handleToggleSelect}
          processedDialogs={[
            ...processingStatus.lastProcessed,
            ...apiSelectedDialogs.map(d => d.id)
          ]}
        />

        {/* Show empty state for selected dialogs */}
        {activeTab === 'selected' && apiSelectedDialogs.length === 0 && !loadingSelected && (
          <div className="text-center text-gray-500 dark:text-gray-400 py-8 my-4 bg-white dark:bg-gray-800 rounded-lg shadow">
            <p className="mb-2">No dialogs selected for processing.</p>
            <p className="text-sm">Select dialogs from other tabs and click &quot;Process Selected&quot; to add them here.</p>
          </div>
        )}
      </div>
    </AppLayout>
  );
}

