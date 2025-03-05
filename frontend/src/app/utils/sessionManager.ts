/**
 * Session management utilities for the Telegram Dialog Processor
 */

// Key used for storing the JWT token in localStorage
const TOKEN_KEY = 'jwt_token';

/**
 * Interface for JWT token payload
 */
interface JwtPayload {
  user_id: number;
  exp: number;
  iat: number;
  is_authenticated: boolean;
  telegram_id?: number;
}

/**
 * Get the current JWT token from localStorage
 * @returns The JWT token or null if not set
 */
export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * Set a JWT token in localStorage
 * @param token The JWT token to store
 */
export function setToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
}

/**
 * Clear the JWT token from localStorage
 */
export function clearToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * Check if there is a valid JWT token stored
 * @returns True if a JWT token is stored
 */
export function hasToken(): boolean {
  return !!getToken();
}

/**
 * Create API URL with authorization header
 * @param endpoint The API endpoint path
 * @returns Full API URL
 */
export function createApiUrl(endpoint: string): string {
  // Just ensure the URL is properly formatted
  return endpoint;
}

/**
 * Create headers for API requests with JWT token
 * @returns Headers object with content type and authorization token
 */
export function createApiHeaders(): HeadersInit {
  const token = getToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
}

/**
 * Determine if we're in development mode
 * @returns True if in development mode
 */
export function isDevelopmentMode(): boolean {
  return process.env.NODE_ENV === 'development';
}

/**
 * Parse JWT token to get payload data
 * @param token The JWT token to parse
 * @returns The decoded payload or null if invalid
 */
export function parseJwtToken(token: string): JwtPayload | null {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
      return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));

    return JSON.parse(jsonPayload) as JwtPayload;
  } catch (e) {
    console.error('Error parsing JWT token:', e);
    return null;
  }
}

/**
 * Check if a JWT token is expired
 * @param token The JWT token to check
 * @returns True if the token is expired or invalid
 */
export function isTokenExpired(token: string): boolean {
  const payload = parseJwtToken(token);
  if (!payload || !payload.exp) return true;
  
  const expirationTime = payload.exp * 1000; // Convert to milliseconds
  const currentTime = Date.now();
  
  return currentTime >= expirationTime;
} 