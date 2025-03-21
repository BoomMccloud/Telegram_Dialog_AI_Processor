import { useState, useCallback, useEffect } from 'react';
import { api } from '../services/api';
import { Response } from '../types';
import { useDialogUUID } from './useDialogUUID';

interface UseDialogResponseResult {
  response: Response | null;
  loading: boolean;
  error: Error | null;
  setSelectedResponse: (response: Response | null) => void;
}

/**
 * Hook to get the response for a dialog using its Telegram ID
 * @param telegramId The Telegram dialog ID
 * @returns Object containing the response, loading state, and error state
 */
export const useDialogResponse = (telegramId: string | null): UseDialogResponseResult => {
  const { uuid, loading: uuidLoading, error: uuidError, getUUID } = useDialogUUID(telegramId);
  const [response, setResponse] = useState<Response | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchResponse = useCallback(async () => {
    if (!uuid) {
      setResponse(null);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const responses = await api.responses.getPending();
      const dialogResponse = responses.responses.find(r => r.dialog_id === uuid);
      setResponse(dialogResponse || null);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to get dialog response');
      setError(error);
    } finally {
      setLoading(false);
    }
  }, [uuid]);

  useEffect(() => {
    if (telegramId) {
      getUUID().then(() => fetchResponse());
    } else {
      setResponse(null);
    }
  }, [telegramId, getUUID, fetchResponse]);

  return {
    response,
    loading: loading || uuidLoading,
    error: error || uuidError,
    setSelectedResponse: setResponse
  };
}; 