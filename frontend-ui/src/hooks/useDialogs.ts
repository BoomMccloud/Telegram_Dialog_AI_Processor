import { useState, useEffect, useCallback } from 'react';
import { api } from '@services/api';

interface ApiDialog {
  id: number;
  name: string;
  unread_count: number;
  is_group: boolean;
  is_channel: boolean;
  is_user: boolean;
  type: string;
}

interface ApiDialogResponse {
  dialogs: ApiDialog[];
}

export interface Dialog {
  id: number;
  title: string;
  unread_count: number;
  is_group: boolean;
  has_mention: boolean;
  last_message?: {
    text: string;
    date: string;
  };
}

export type DialogFilterMode = 'all-unread' | 'unread-dms' | 'unread-groups' | 'all';

export interface UseDialogsResult {
  dialogs: Dialog[];
  filteredDialogs: Dialog[];
  loading: boolean;
  error: Error | null;
  fetchDialogs: () => Promise<void>;
  selectedDialogId: string | null;
  setSelectedDialogId: (id: string | null) => void;
  filterMode: DialogFilterMode;
  setFilterMode: (mode: DialogFilterMode) => void;
  initialized: boolean;
}

const STORAGE_KEYS = {
  DIALOGS: 'telegram_dialogs',
  FILTER_MODE: 'telegram_filter_mode',
  SELECTED_DIALOG: 'telegram_selected_dialog',
  INITIALIZED: 'telegram_initialized'
};

export const useDialogs = (): UseDialogsResult => {
  const [dialogs, setDialogs] = useState<Dialog[]>(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.DIALOGS);
    return saved ? JSON.parse(saved) : [];
  });
  
  const [filteredDialogs, setFilteredDialogs] = useState<Dialog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [selectedDialogId, setSelectedDialogId] = useState<string | null>(() => {
    return localStorage.getItem(STORAGE_KEYS.SELECTED_DIALOG);
  });
  const [filterMode, setFilterMode] = useState<DialogFilterMode>(() => {
    return (localStorage.getItem(STORAGE_KEYS.FILTER_MODE) as DialogFilterMode) || 'all-unread';
  });
  const [initialized, setInitialized] = useState<boolean>(() => {
    return localStorage.getItem(STORAGE_KEYS.INITIALIZED) === 'true';
  });

  // Persist state changes to localStorage
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.DIALOGS, JSON.stringify(dialogs));
  }, [dialogs]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.FILTER_MODE, filterMode);
  }, [filterMode]);

  useEffect(() => {
    if (selectedDialogId) {
      localStorage.setItem(STORAGE_KEYS.SELECTED_DIALOG, selectedDialogId);
    } else {
      localStorage.removeItem(STORAGE_KEYS.SELECTED_DIALOG);
    }
  }, [selectedDialogId]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.INITIALIZED, initialized.toString());
  }, [initialized]);

  const filterDialogs = useCallback((dialogList: Dialog[], mode: DialogFilterMode) => {
    switch (mode) {
      case 'all-unread':
        return dialogList.filter(dialog => dialog.unread_count > 0);
      case 'unread-dms':
        return dialogList.filter(dialog => dialog.unread_count > 0 && !dialog.is_group);
      case 'unread-groups':
        return dialogList.filter(dialog => dialog.unread_count > 0 && dialog.is_group);
      case 'all':
        return dialogList;
      default:
        return dialogList;
    }
  }, []);

  const fetchDialogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.dialogs.getAll() as ApiDialogResponse;
      if (!response || !response.dialogs) {
        throw new Error('Invalid response format from server');
      }
      
      // Transform the response to match our Dialog interface
      const transformedDialogs = response.dialogs.map((dialog: ApiDialog) => ({
        id: dialog.id,
        title: dialog.name,
        unread_count: dialog.unread_count,
        is_group: dialog.is_group || dialog.is_channel,
        has_mention: false, // We'll need to get this from messages
        last_message: undefined // We'll need to get this from messages
      }));
      
      setDialogs(transformedDialogs);
      setFilteredDialogs(filterDialogs(transformedDialogs, filterMode));
      setInitialized(true);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch dialogs'));
      console.error('Error fetching dialogs:', err);
    } finally {
      setLoading(false);
    }
  }, [filterMode, filterDialogs]);

  // Auto-fetch dialogs on mount if we don't have any
  useEffect(() => {
    if (!initialized && dialogs.length === 0) {
      fetchDialogs();
    }
  }, [initialized, dialogs.length, fetchDialogs]);

  // Update filtered dialogs when filter mode changes
  useEffect(() => {
    setFilteredDialogs(filterDialogs(dialogs, filterMode));
  }, [dialogs, filterMode, filterDialogs]);

  // Set up periodic refresh (every 30 seconds)
  useEffect(() => {
    const intervalId = setInterval(fetchDialogs, 30000);
    return () => clearInterval(intervalId);
  }, [fetchDialogs]);

  return {
    dialogs,
    filteredDialogs,
    loading,
    error,
    fetchDialogs,
    selectedDialogId,
    setSelectedDialogId,
    filterMode,
    setFilterMode,
    initialized,
  };
}; 