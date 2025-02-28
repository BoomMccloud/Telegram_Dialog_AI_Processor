'use client';

import dynamic from 'next/dynamic';

// Import DevTools with client-side only rendering
const DevTools = dynamic(() => import('./DevTools'), {
  ssr: false, // Disable server-side rendering
});

export default function DevToolsWrapper() {
  return <DevTools />;
} 