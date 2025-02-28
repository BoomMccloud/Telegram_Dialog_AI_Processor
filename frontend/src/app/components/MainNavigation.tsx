'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTheme } from '../ThemeContext';
import { MoonIcon, SunIcon } from '@heroicons/react/24/outline';

interface NavigationItem {
  name: string;
  href: string;
}

export default function MainNavigation() {
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();
  
  const navigation: NavigationItem[] = [
    { name: 'Home', href: '/home' },
    { name: 'Chats', href: '/chats' },
    { name: 'Data Source', href: '/messages' },
  ];

  // Function to determine if a nav item is active
  const isActive = (path: string) => {
    // Special case for root path
    if (path === '/home' && pathname === '/') {
      return true;
    }
    
    // Check if the pathname starts with the path (for nested routes)
    return pathname.startsWith(path);
  };

  return (
    <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <span className="text-xl font-bold text-gray-900 dark:text-white">
                Telegram Dialog Processor
              </span>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`
                    inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium
                    ${isActive(item.href)
                      ? 'border-blue-500 text-gray-900 dark:text-white dark:border-blue-400'
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-300 dark:hover:text-white dark:hover:border-gray-600'
                    }
                  `}
                >
                  {item.name}
                </Link>
              ))}
            </div>
          </div>
          <div className="flex items-center">
            <button
              onClick={toggleTheme}
              className="rounded-full p-2 bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-300 hover:text-gray-700 dark:hover:text-white focus:outline-none"
              aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? (
                <SunIcon className="h-5 w-5" />
              ) : (
                <MoonIcon className="h-5 w-5" />
              )}
            </button>
          </div>
        </div>
      </div>
      
      {/* Mobile navigation */}
      <div className="sm:hidden">
        <div className="pt-2 pb-3 space-y-1">
          {navigation.map((item) => (
            <Link
              key={item.name}
              href={item.href}
              className={`
                block pl-3 pr-4 py-2 border-l-4 text-base font-medium
                ${isActive(item.href)
                  ? 'bg-blue-50 border-blue-500 text-blue-700 dark:bg-gray-700 dark:border-blue-400 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-700 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white dark:hover:border-gray-600'
                }
              `}
            >
              {item.name}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
} 