import { useState } from 'react';
import { api } from '../services/api';
import { Response, ResponseStatus } from '../types';

interface UseResponsesResult {
  pendingResponses: Response[];
  historyResponses: Response[];
  totalPending: number;
  totalHistory: number;
  selectedResponse: Response | null;
  loading: boolean;
  error: string | null;
  fetchPendingResponses: () => Promise<void>;
  fetchHistoryResponses: (statusFilter?: string) => Promise<void>;
  approveResponse: (responseId: string) => Promise<boolean>;
  rejectResponse: (responseId: string) => Promise<boolean>;
  updateResponse: (responseId: string, editedText: string) => Promise<boolean>;
  sendResponse: (responseId: string) => Promise<boolean>;
  setSelectedResponse: (response: Response | null) => void;
  setPendingResponses: (responses: Response[]) => void;
  setHistoryResponses: (responses: Response[]) => void;
  setTotalPending: (total: number) => void;
  setTotalHistory: (total: number) => void;
}

export const useResponses = (): UseResponsesResult => {
  const [pendingResponses, setPendingResponses] = useState<Response[]>([]);
  const [historyResponses, setHistoryResponses] = useState<Response[]>([]);
  const [totalPending, setTotalPending] = useState(0);
  const [totalHistory, setTotalHistory] = useState(0);
  const [selectedResponse, setSelectedResponse] = useState<Response | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch pending responses
  const fetchPendingResponses = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.responses.getPending(0, 100);
      setPendingResponses(response.responses);
      setTotalPending(response.total);
    } catch (err: unknown) {
      console.error('Error fetching pending responses:', err);
      
      // Check for authentication error
      if (err instanceof Error && err.message === 'AUTH_REQUIRED') {
        setError('Authentication required. Please log in.');
      } else if (typeof err === 'object' && err !== null && 'response' in err && 
                (err.response as { status?: number })?.status === 401) {
        setError('Authentication required. Please log in.');
      } else {
        setError('Failed to load pending responses. Please try again later.');
      }
      
      setPendingResponses([]);
      setTotalPending(0);
    } finally {
      setLoading(false);
    }
  };

  // Fetch history responses
  const fetchHistoryResponses = async (statusFilter?: string): Promise<void> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.responses.getHistory(
        0, 
        100,
        statusFilter !== 'all' ? statusFilter : undefined
      );
      
      setHistoryResponses(response.responses);
      setTotalHistory(response.total);
    } catch (err: unknown) {
      console.error('Error fetching history responses:', err);
      
      // Check for authentication error
      if (err instanceof Error && err.message === 'AUTH_REQUIRED') {
        setError('Authentication required. Please log in.');
      } else if (typeof err === 'object' && err !== null && 'response' in err && 
                (err.response as { status?: number })?.status === 401) {
        setError('Authentication required. Please log in.');
      } else {
        setError('Failed to load response history. Please try again later.');
      }
      
      setHistoryResponses([]);
      setTotalHistory(0);
    } finally {
      setLoading(false);
    }
  };

  // Approve response
  const approveResponse = async (responseId: string): Promise<boolean> => {
    try {
      await api.responses.approve(responseId);
      
      // Update the selected response if it's the one being approved
      if (selectedResponse && selectedResponse.id === responseId) {
        setSelectedResponse({
          ...selectedResponse,
          status: ResponseStatus.APPROVED
        });
      }
      
      // Refresh response lists
      await fetchPendingResponses();
      await fetchHistoryResponses();
      
      return true;
    } catch (err) {
      console.error('Error approving response:', err);
      setError('Failed to approve response. Please try again.');
      return false;
    }
  };

  // Reject response
  const rejectResponse = async (responseId: string): Promise<boolean> => {
    try {
      await api.responses.reject(responseId);
      
      // Update the selected response if it's the one being rejected
      if (selectedResponse && selectedResponse.id === responseId) {
        setSelectedResponse({
          ...selectedResponse,
          status: ResponseStatus.REJECTED
        });
      }
      
      // Refresh response lists
      await fetchPendingResponses();
      await fetchHistoryResponses();
      
      return true;
    } catch (err) {
      console.error('Error rejecting response:', err);
      setError('Failed to reject response. Please try again.');
      return false;
    }
  };

  // Update response
  const updateResponse = async (responseId: string, editedText: string): Promise<boolean> => {
    try {
      await api.responses.update(responseId, { edited_response: editedText });
      
      // Update the selected response if it's the one being edited
      if (selectedResponse && selectedResponse.id === responseId) {
        setSelectedResponse({
          ...selectedResponse,
          edited_response: editedText
        });
      }
      
      // Refresh response lists
      await fetchPendingResponses();
      await fetchHistoryResponses();
      
      return true;
    } catch (err) {
      console.error('Error updating response:', err);
      setError('Failed to update response. Please try again.');
      return false;
    }
  };

  // Send response
  const sendResponse = async (responseId: string): Promise<boolean> => {
    try {
      await api.responses.send(responseId);
      
      // Update the selected response if it's the one being sent
      if (selectedResponse && selectedResponse.id === responseId) {
        setSelectedResponse({
          ...selectedResponse,
          status: ResponseStatus.SENT
        });
      }
      
      // Refresh response lists
      await fetchPendingResponses();
      await fetchHistoryResponses();
      
      return true;
    } catch (err) {
      console.error('Error sending response:', err);
      setError('Failed to send response. Please try again.');
      return false;
    }
  };

  return {
    pendingResponses,
    historyResponses,
    totalPending,
    totalHistory,
    selectedResponse,
    loading,
    error,
    fetchPendingResponses,
    fetchHistoryResponses,
    approveResponse,
    rejectResponse,
    updateResponse,
    sendResponse,
    setSelectedResponse,
    setPendingResponses,
    setHistoryResponses,
    setTotalPending,
    setTotalHistory
  };
}; 