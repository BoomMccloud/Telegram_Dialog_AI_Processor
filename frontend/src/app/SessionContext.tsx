'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export interface User {
    telegram_id: number;
    username?: string;
    first_name?: string;
    last_name?: string;
}

export interface Session {
    id: string;
    token: string;
    status: 'pending' | 'authenticated' | 'error' | 'expired';
    telegram_id?: number;
    expires_at: string;
    user?: User;
}

interface SessionContextType {
    session: Session | null;
    loading: boolean;
    error: string | null;
    isAuthenticated: boolean;
    login: (token: string, sessionId: string, status?: 'pending' | 'authenticated') => void;
    logout: () => Promise<void>;
    checkSession: () => Promise<void>;
}

export const SessionContext = createContext<SessionContextType | undefined>(undefined);

export function SessionProvider({ children }: { children: React.ReactNode }) {
    const [session, setSession] = useState<Session | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const router = useRouter();

    const isAuthenticated = session?.status === 'authenticated';

    useEffect(() => {
        const token = localStorage.getItem('session_token');
        const sessionId = localStorage.getItem('session_id');
        if (token && sessionId) {
            checkSession();
        } else {
            setLoading(false);
        }

        // Check session every minute
        const interval = setInterval(checkSession, 60000);
        return () => clearInterval(interval);
    }, []);

    // Check if session is expired
    useEffect(() => {
        if (session?.expires_at) {
            const expiresAt = new Date(session.expires_at);
            const now = new Date();
            if (expiresAt <= now) {
                logout();
            } else {
                // Set timeout to logout when session expires
                const timeout = setTimeout(() => {
                    logout();
                }, expiresAt.getTime() - now.getTime());
                return () => clearTimeout(timeout);
            }
        }
    }, [session?.expires_at]);

    const login = (token: string, sessionId: string, status: 'pending' | 'authenticated' = 'pending') => {
        localStorage.setItem('session_token', token);
        localStorage.setItem('session_id', sessionId);
        setSession({
            id: sessionId,
            token,
            status,
            expires_at: new Date(Date.now() + 10 * 60 * 1000).toISOString() // 10 minutes for QR sessions
        });
        setError(null);
    };

    const logout = async () => {
        const token = localStorage.getItem('session_token');
        if (token) {
            try {
                await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/logout`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
            } catch (err) {
                console.error('Logout failed:', err);
            }
        }
        localStorage.removeItem('session_token');
        localStorage.removeItem('session_id');
        setSession(null);
        setError(null);
        router.push('/');
    };

    const checkSession = async () => {
        const token = localStorage.getItem('session_token');
        if (!token) {
            setSession(null);
            setLoading(false);
            return;
        }

        try {
            setLoading(true);
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/api/auth/session/verify`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                }
            );

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('Session expired');
                }
                throw new Error('Session verification failed');
            }

            const data = await response.json();
            setSession({
                id: localStorage.getItem('session_id') || '',
                token,
                status: data.status,
                telegram_id: data.telegram_id,
                expires_at: data.expires_at,
                user: data.user
            });
            setError(null);

        } catch (err) {
            console.error('Session check failed:', err);
            localStorage.removeItem('session_token');
            localStorage.removeItem('session_id');
            setSession(null);
            setError(err instanceof Error ? err.message : 'Session verification failed');
            router.push('/');
        } finally {
            setLoading(false);
        }
    };

    return (
        <SessionContext.Provider value={{
            session,
            loading,
            error,
            isAuthenticated,
            login,
            logout,
            checkSession
        }}>
            {children}
        </SessionContext.Provider>
    );
}

export function useSession() {
    const context = useContext(SessionContext);
    if (context === undefined) {
        throw new Error('useSession must be used within a SessionProvider');
    }
    return context;
} 