import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return 'N/A';
  return new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function formatDateTime(date: string | null | undefined): string {
  if (!date) return 'N/A';
  return new Date(date).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatCurrency(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return 'N/A';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(amount);
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    // Job status
    PENDING: 'bg-yellow-100 text-yellow-800',
    RUNNING: 'bg-blue-100 text-blue-800',
    COMPLETED: 'bg-green-100 text-green-800',
    FAILED: 'bg-red-100 text-red-800',
    CANCELLED: 'bg-gray-100 text-gray-800',
    // Item status
    DRAFT: 'bg-gray-100 text-gray-800',
    NEEDS_REVIEW: 'bg-yellow-100 text-yellow-800',
    VERIFIED: 'bg-blue-100 text-blue-800',
    PUBLISHED: 'bg-green-100 text-green-800',
    OUTDATED: 'bg-orange-100 text-orange-800',
    ARCHIVED: 'bg-gray-100 text-gray-800',
    // URL status
    DISCOVERED: 'bg-gray-100 text-gray-800',
    CLASSIFIED: 'bg-blue-100 text-blue-800',
    SCRAPED: 'bg-purple-100 text-purple-800',
    EXTRACTED: 'bg-green-100 text-green-800',
    SKIPPED: 'bg-gray-100 text-gray-800',
    ERROR: 'bg-red-100 text-red-800',
    // Relevance
    RELEVANT: 'bg-green-100 text-green-800',
    NOT_RELEVANT: 'bg-gray-100 text-gray-800',
    // Priority
    HIGH: 'bg-red-100 text-red-800',
    MEDIUM: 'bg-yellow-100 text-yellow-800',
    LOW: 'bg-gray-100 text-gray-800',
  };
  return colors[status] || 'bg-gray-100 text-gray-800';
}

export function getItemTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    PROGRAM: 'Program',
    SCHOLARSHIP: 'Scholarship',
    CONFERENCE: 'Conference',
    EXCHANGE: 'Exchange',
  };
  return labels[type] || type;
}

export function getSourceTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    UNIVERSITY: 'University',
    SCHOLARSHIP_ORG: 'Scholarship Org',
    CONFERENCE_ORG: 'Conference Org',
    EXCHANGE_ORG: 'Exchange Org',
    OTHER: 'Other',
  };
  return labels[type] || type;
}
