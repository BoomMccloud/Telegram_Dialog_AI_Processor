'use client';

import { useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import MainNavigation from './components/MainNavigation';
import { useSession } from './SessionContext';

interface AppLayoutProps {
  children: ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  const router = useRouter();
  const { isAuthenticated } = useSession();
  
  // Check authentication on mount and redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/');
    }
  }, [router, isAuthenticated]);

  return (
    <div className="flex flex-col min-h-screen bg-gray-50 dark:bg-gray-900">
      <MainNavigation />
      <main className="flex-grow px-4 py-6 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  );
} 