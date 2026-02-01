'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home,
  Database,
  Link2,
  FileText,
  Activity,
  Settings,
  LogOut,
  CheckSquare,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/lib/store';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: Home },
  { name: 'Sources', href: '/sources', icon: Database },
  { name: 'URLs', href: '/urls', icon: Link2 },
  { name: 'Items', href: '/items', icon: FileText },
  { name: 'Review Queue', href: '/review', icon: CheckSquare },
  { name: 'Jobs', href: '/jobs', icon: Activity },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
  };

  return (
    <div className="flex h-screen w-64 flex-col bg-gray-900">
      {/* Logo */}
      <div className="flex h-16 items-center justify-center border-b border-gray-800">
        <h1 className="text-xl font-bold text-white">Data Portal</h1>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-2 py-4">
        {navigation.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'group flex items-center rounded-md px-3 py-2 text-sm font-medium',
                isActive
                  ? 'bg-gray-800 text-white'
                  : 'text-gray-300 hover:bg-gray-700 hover:text-white'
              )}
            >
              <item.icon
                className={cn(
                  'mr-3 h-5 w-5 flex-shrink-0',
                  isActive
                    ? 'text-white'
                    : 'text-gray-400 group-hover:text-white'
                )}
              />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* User section */}
      <div className="border-t border-gray-800 p-4">
        <div className="flex items-center">
          <div className="flex-1">
            <p className="text-sm font-medium text-white">{user?.name || user?.email}</p>
            <p className="text-xs text-gray-400">{user?.role}</p>
          </div>
          <button
            onClick={handleLogout}
            className="rounded-md p-2 text-gray-400 hover:bg-gray-700 hover:text-white"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
