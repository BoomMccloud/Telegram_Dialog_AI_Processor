import { api } from './api';
import { SessionStatus, QRAuthResponse } from '../types';
import axios from 'axios';

/**
 * Check if the user is already authenticated
 */
export const checkAuthentication = async (): Promise<boolean> => {
  try {
    const session = await api.auth.verifySession();
    return session.status === SessionStatus.AUTHENTICATED;
  } catch (error) {
    console.error('Authentication check failed:', error);
    return false;
  }
};

/**
 * Initialize QR code authentication
 */
export const initiateQRAuthentication = async (): Promise<QRAuthResponse> => {
  try {
    return await api.auth.createQRAuth();
  } catch (error) {
    console.error('QR authentication initiation failed:', error);
    throw error;
  }
};

/**
 * Poll the session status until authentication is complete or timeout
 * @param callback Function to call with updated session status
 * @param maxAttempts Maximum number of attempts before giving up
 * @param initialDelay Initial delay between polls in ms
 */
export const pollSessionStatus = async (
  callback: (status: SessionStatus, error?: Error) => void, 
  maxAttempts = 5,
  initialDelay = 2000
): Promise<void> => {
  let attempts = 0;
  let delay = initialDelay;
  
  const poll = async () => {
    attempts++;
    console.log(`[Auth Debug] Polling attempt ${attempts}/${maxAttempts}`);
    
    if (attempts >= maxAttempts) {
      console.log(`[Auth Debug] Max attempts (${maxAttempts}) reached, giving up`);
      callback(SessionStatus.ERROR, new Error('Polling timeout'));
      return;
    }
    
    try {
      console.log(`[Auth Debug] Sending verify session request...`);
      const response = await api.auth.verifySession();
      console.log(`[Auth Debug] Session status: ${response.status}`, response);
      
      // Store tokens if they're in the response
      if (response.access_token) {
        console.log('[Auth Debug] Storing access token from poll response');
        localStorage.setItem('accessToken', response.access_token);
        
        if (response.refresh_token) {
          console.log('[Auth Debug] Storing refresh token from poll response');
          localStorage.setItem('refreshToken', response.refresh_token);
        }
      }
      
      callback(response.status);
      
      if (response.status === SessionStatus.AUTHENTICATED) {
        console.log('[Auth Debug] Successfully authenticated!', response);
        
        // Double check token storage
        const hasAccessToken = !!localStorage.getItem('accessToken');
        const hasRefreshToken = !!localStorage.getItem('refreshToken');
        console.log(`[Auth Debug] Tokens in localStorage: access=${hasAccessToken}, refresh=${hasRefreshToken}`);
        
        return;
      } else if (response.status === SessionStatus.PENDING) {
        console.log(`[Auth Debug] Session still pending, waiting ${delay}ms before next attempt`);
        // Increase delay slightly for each attempt
        delay = Math.min(delay * 1.2, 5000);
        setTimeout(poll, delay);
      } else if (response.status === SessionStatus.UNAUTHENTICATED) {
        console.log(`[Auth Debug] Session is unauthenticated`);
        // User hasn't authenticated yet, continue polling
        delay = Math.min(delay * 1.2, 5000);
        setTimeout(poll, delay);
      } else {
        console.log(`[Auth Debug] Session in terminal state: ${response.status}`);
        // Error or expired
        return;
      }
    } catch (error) {
      console.error('[Auth Debug] Error polling session status:', error);
      
      // Attempt to extract useful info from error
      if (axios.isAxiosError(error)) {
        console.log(`[Auth Debug] Status: ${error.response?.status}, Message: ${error.message}`);
        if (error.response?.data) {
          console.log('[Auth Debug] Error response data:', error.response.data);
        }
      }
      
      // Keep polling despite errors, with increased delay
      delay = Math.min(delay * 1.5, 8000);
      console.log(`[Auth Debug] Will retry in ${delay}ms`);
      setTimeout(poll, delay);
    }
  };
  
  console.log('[Auth Debug] Starting session status polling...');
  poll();
};

/**
 * Logout the current user
 */
export const logout = async (): Promise<void> => {
  try {
    // Only attempt logout if we have a token
    if (localStorage.getItem('accessToken')) {
      await api.auth.logout();
    }
  } catch (error) {
    console.error('Logout failed:', error);
  } finally {
    // Always clear local storage
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('tempSessionId');
  }
};

/**
 * Handle QR code scanning
 * This is a utility function that offers guidance based on common issues
 */
export const getQRScanningTip = (): string => {
  return "Open Telegram on your mobile device, go to Settings → Devices → Scan QR Code";
};

/**
 * Developer login for testing (only works in development mode)
 * @param telegramId The Telegram user ID to log in with
 */
export const devLogin = async (telegramId: number): Promise<boolean> => {
  try {
    console.log(`[Auth Debug] Attempting dev login with ID: ${telegramId}`);
    const response = await api.auth.devLogin(telegramId);
    
    // Handle both token formats (backend returns single token)
    if (response.access_token) {
      console.log('[Auth Debug] Dev login successful, storing tokens (access_token format)');
      localStorage.setItem('accessToken', response.access_token);
      
      if (response.refresh_token) {
        localStorage.setItem('refreshToken', response.refresh_token);
      }
      
      return true;
    } else if (response.token) {
      // Backend returns a single token field
      console.log('[Auth Debug] Dev login successful, storing token (token format)');
      localStorage.setItem('accessToken', response.token);
      return true;
    }
    
    console.log('[Auth Debug] Dev login response had no token:', response);
    return false;
  } catch (error) {
    console.error('[Auth Debug] Dev login failed:', error);
    return false;
  }
};

/**
 * Initialize phone number authentication by sending verification code
 * @param phoneNumber Phone number with country code (e.g. '+15551234567')
 */
export const initiatePhoneAuthentication = async (phoneNumber: string): Promise<{
  sessionId: string;
  expiresAt: string;
  phoneCodeHash: string;
}> => {
  try {
    console.log(`[Auth Debug] Initiating phone auth for number: ${phoneNumber}`);
    const response = await api.auth.initiatePhoneAuth(phoneNumber);
    
    // Store the session ID temporarily
    localStorage.setItem('tempSessionId', response.session_id);
    
    return {
      sessionId: response.session_id,
      expiresAt: response.expires_at,
      phoneCodeHash: response.phone_code_hash
    };
  } catch (error) {
    console.error('Phone authentication initiation failed:', error);
    throw error;
  }
};

/**
 * Verify phone code to complete authentication
 * @param phoneNumber Phone number with country code
 * @param code Verification code received via SMS
 * @param sessionId Session ID from initiatePhoneAuthentication
 */
export const verifyPhoneCode = async (
  phoneNumber: string,
  code: string,
  sessionId: string
): Promise<boolean> => {
  try {
    console.log(`[Auth Debug] Verifying phone code for session: ${sessionId}`);
    const response = await api.auth.verifyPhoneCode(phoneNumber, code, sessionId);
    
    if (response.status === SessionStatus.AUTHENTICATED) {
      console.log('[Auth Debug] Phone verification successful!', response);
      
      // Store the access token if available
      if (response.access_token) {
        localStorage.setItem('accessToken', response.access_token);
        
        // Store refresh token if available
        if (response.refresh_token) {
          localStorage.setItem('refreshToken', response.refresh_token);
        }
      } else {
        // If no access_token in response, get one by verifying the session
        console.log('[Auth Debug] No access token in phone verification response, fetching from session verify');
        try {
          const sessionResponse = await api.auth.verifySession();
          if (sessionResponse.status === SessionStatus.AUTHENTICATED && sessionResponse.access_token) {
            console.log('[Auth Debug] Got access token from session verify:', sessionResponse.access_token);
            localStorage.setItem('accessToken', sessionResponse.access_token);
            
            if (sessionResponse.refresh_token) {
              localStorage.setItem('refreshToken', sessionResponse.refresh_token);
            }
          } else {
            console.warn('[Auth Debug] Session verified but no access token returned');
          }
        } catch (sessionError) {
          console.error('[Auth Debug] Failed to verify session after phone authentication:', sessionError);
        }
      }
      
      return true;
    }
    
    return false;
  } catch (error) {
    console.error('Phone code verification failed:', error);
    throw error;
  }
}; 