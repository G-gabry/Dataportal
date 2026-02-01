'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from './Sidebar';
import { useAuthStore } from '@/lib/store';

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { token, _hasHydrated } = useAuthStore();

  useEffect(() => {
    // Wait for hydration before checking auth
    if (_hasHydrated && !token) {
      router.push('/login');
    }
  }, [token, _hasHydrated, router]);

  // Show loading while hydrating or if not authenticated
  if (!_hasHydrated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent"></div>
      </div>
    );
  }

  // If hydrated but no token, show loading while redirecting
  if (!token) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent"></div>
      </div>
    );
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-auto bg-gray-50">
        <div className="p-8">{children}</div>
      </main>
    </div>
  );
}
