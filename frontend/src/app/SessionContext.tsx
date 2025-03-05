'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export interface Session {
    token: string;
    status: 'pending' | 'authenticated' | 'error' | 'expired';
    telegram_id?: number;
    expires_at?: string;
}

interface SessionContextType {
    session: Session | null;
    loading: boolean;
    error: string | null;
    isAuthenticated: boolean;
    login: (token?: string, status?: string) => void;
    logout: () => void;
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
        if (token) {
            checkSession();
        } else {
            setLoading(false);
        }

        const interval = setInterval(checkSession, 60000);
        return () => clearInterval(interval);
    }, []);

    const login = (token?: string, status: string = 'pending') => {
        if (token) {
            localStorage.setItem('session_token', token);
            setSession({
                token,
                status: status as Session['status']
            });
            setError(null);
        }
    };

    const logout = () => {
        localStorage.removeItem('session_token');
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
                `${process.env.NEXT_PUBLIC_API_URL}/api/auth/session/verify?token=${token}`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                }
            );

            if (!response.ok) {
                throw new Error('Session invalid');
            }

            const data = await response.json();
            setSession({
                token,
                ...data
            });
            setError(null);

        } catch (err) {
            console.error('Session check failed:', err);
            localStorage.removeItem('session_token');
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