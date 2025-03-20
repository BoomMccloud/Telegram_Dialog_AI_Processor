import { useState } from 'react';
import { api } from '../services/api';
import { BaseDialog } from '../types';
import { DialogMessage } from '../types/dialog';

interface UseDialogsResult {
  dialogs: BaseDialog[];
  selectedDialog: BaseDialog | null;
  dialogMessages: DialogMessage[];
  loading: boolean;
  loadingMessages: boolean;
  error: string | null;
  fetchDialogs: () => Promise<void>;
  fetchDialogMessages: (dialogId: string) => Promise<void>;
  setSelectedDialog: (dialog: BaseDialog | null) => void;
  refreshDialogs: () => Promise<void>;
  isProcessing: boolean;
  processingProgress: {
    totalDialogs: number;
    processedDialogs: number;
    currentDialogName: string;
    currentOperation: string;
    error: string | null;
  };
  startProcessing: () => Promise<void>;
  cancelProcessing: () => void;
}

export const useDialogs = (): UseDialogsResult => {
  const [dialogs, setDialogs] = useState<BaseDialog[]>([]);
  const [selectedDialog, setSelectedDialog] = useState<BaseDialog | null>(null);
  const [dialogMessages, setDialogMessages] = useState<DialogMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingProgress, setProcessingProgress] = useState({
    totalDialogs: 0,
    processedDialogs: 0,
    currentDialogName: '',
    currentOperation: '',
    error: null as string | null
  });

  // Fetch all dialogs
  const fetchDialogs = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.telegram.getDialogs();
      setDialogs(response.dialogs);
    } catch (err) {
      console.error('Error fetching dialogs:', err);
      setError('Failed to load dialogs. Please try again later.');
      setDialogs([]);
    } finally {
      setLoading(false);
    }
  };

  // Fetch messages for a specific dialog
  const fetchDialogMessages = async (dialogId: string): Promise<void> => {
    setLoadingMessages(true);
    
    try {
      // Implement when API is ready
      // const response = await api.messages.getByDialogId(dialogId);
      // setDialogMessages(response.messages);
      
      // Mock data for now
      console.log(`Fetching messages for dialog: ${dialogId}`);
      setDialogMessages([]);
    } catch (err) {
      console.error('Error fetching dialog messages:', err);
      setError('Failed to load dialog messages. Please try again later.');
      setDialogMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  };

  // Refresh dialogs (for the manual refresh button)
  const refreshDialogs = async (): Promise<void> => {
    await fetchDialogs();
  };

  // Start processing dialogs
  const startProcessing = async (): Promise<void> => {
    console.log('Starting refresh process...');
    setIsProcessing(true);
    setProcessingProgress({
      totalDialogs: 0,
      processedDialogs: 0,
      currentDialogName: '',
      currentOperation: 'Fetching dialogs...',
      error: null
    });

    try {
      // Fetch all dialogs
      const dialogsResponse = await api.telegram.getDialogs();
      console.log('Received dialogs:', dialogsResponse);
      
      // Filter dialogs based on criteria
      const filteredDialogs = dialogsResponse.dialogs.filter(dialog => {
        return (dialog.is_user && dialog.unread_count > 0) || // Unread private messages
               (!dialog.is_user && dialog.unread_count > 0 && dialog.type === 'group'); // Unread group messages
      });

      console.log('Filtered dialogs:', filteredDialogs);
      
      // Update state with filtered dialogs
      setDialogs(filteredDialogs);
      
      // Update progress
      setProcessingProgress(prev => ({
        ...prev,
        totalDialogs: filteredDialogs.length,
        currentOperation: 'Processing dialogs...'
      }));

      // Process each dialog and generate responses
      for (const dialog of filteredDialogs) {
        try {
          setProcessingProgress(prev => ({
            ...prev,
            currentDialogName: dialog.name,
            currentOperation: `Generating responses for ${dialog.name}...`
          }));

          // Generate responses based on dialog type
          if (dialog.is_user) {
            await api.responses.generate.private(dialog.id.toString());
          } else {
            await api.responses.generate.group(dialog.id.toString());
          }

          setProcessingProgress(prev => ({
            ...prev,
            processedDialogs: prev.processedDialogs + 1
          }));

        } catch (dialogError) {
          console.error(`Error processing dialog ${dialog.name}:`, dialogError);
          setProcessingProgress(prev => ({
            ...prev,
            error: `Failed to process ${dialog.name}. Continuing with next dialog...`
          }));
        }
      }

      setProcessingProgress(prev => ({
        ...prev,
        currentOperation: 'All dialogs processed successfully'
      }));

    } catch (err) {
      console.error('Error during refresh:', err);
      setProcessingProgress(prev => ({
        ...prev,
        error: 'Failed to fetch or process dialogs. Please try again.'
      }));
    } finally {
      setIsProcessing(false);
    }
  };

  // Cancel processing
  const cancelProcessing = () => {
    setIsProcessing(false);
  };

  return {
    dialogs,
    selectedDialog,
    dialogMessages,
    loading,
    loadingMessages,
    error,
    fetchDialogs,
    fetchDialogMessages,
    setSelectedDialog,
    refreshDialogs,
    isProcessing,
    processingProgress,
    startProcessing,
    cancelProcessing
  };
}; 