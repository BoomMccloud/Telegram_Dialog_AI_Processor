/**
 * Session management utilities for the Telegram Dialog Processor
 */

// Key used for storing the session ID in localStorage
const SESSION_KEY = 'sessionId';

/**
 * Get the current session ID from localStorage
 * @returns The session ID or null if not set
 */
export function getSessionId(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(SESSION_KEY);
}

/**
 * Set a session ID in localStorage
 * @param sessionId The session ID to store
 */
export function setSessionId(sessionId: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(SESSION_KEY, sessionId);
}

/**
 * Clear the session ID from localStorage
 */
export function clearSessionId(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(SESSION_KEY);
}

/**
 * Check if there is a valid session ID stored
 * @returns True if a session ID is stored
 */
export function hasSession(): boolean {
  return !!getSessionId();
}

/**
 * Create API URL with session ID
 * @param endpoint The API endpoint path (without session ID)
 * @returns Full API URL with session ID included
 */
export function createApiUrl(endpoint: string): string {
  const sessionId = getSessionId();
  if (!sessionId) {
    throw new Error('No session ID available');
  }
  
  // Replace any {session_id} placeholder with the actual session ID
  if (endpoint.includes('{session_id}')) {
    return endpoint.replace('{session_id}', sessionId);
  }
  
  // Otherwise, just ensure the URL is properly formatted
  return endpoint;
}

/**
 * Create headers for API requests
 * @returns Headers object with content type set to JSON
 */
export function createApiHeaders(): HeadersInit {
  return {
    'Content-Type': 'application/json',
  };
}

/**
 * Determine if we're in development mode
 * @returns True if in development mode
 */
export function isDevelopmentMode(): boolean {
  return process.env.NODE_ENV === 'development';
} 