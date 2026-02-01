'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import MainLayout from '@/components/layout/MainLayout';
import Card, { CardHeader, CardContent } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Badge from '@/components/ui/Badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { urls } from '@/lib/api';
import { formatDateTime, getStatusColor, truncate } from '@/lib/utils';
import { ExternalLink, Eye } from 'lucide-react';
import Link from 'next/link';

const statusOptions = [
  { value: '', label: 'All Statuses' },
  { value: 'DISCOVERED', label: 'Discovered' },
  { value: 'CLASSIFIED', label: 'Classified' },
  { value: 'SCRAPED', label: 'Scraped' },
  { value: 'EXTRACTED', label: 'Extracted' },
  { value: 'SKIPPED', label: 'Skipped' },
  { value: 'ERROR', label: 'Error' },
];

const relevanceOptions = [
  { value: '', label: 'All Relevance' },
  { value: 'PENDING', label: 'Pending' },
  { value: 'RELEVANT', label: 'Relevant' },
  { value: 'NOT_RELEVANT', label: 'Not Relevant' },
];

const priorityOptions = [
  { value: '', label: 'All Priorities' },
  { value: 'HIGH', label: 'High' },
  { value: 'MEDIUM', label: 'Medium' },
  { value: 'LOW', label: 'Low' },
];

export default function URLsPage() {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [relevance, setRelevance] = useState('');
  const [priority, setPriority] = useState('');
  const [page, setPage] = useState(1);

  const { data: urlsData, isLoading } = useQuery({
    queryKey: ['urls', search, status, relevance, priority, page],
    queryFn: () =>
      urls.list({
        search: search || undefined,
        status: status || undefined,
        relevance: relevance || undefined,
        priority: priority || undefined,
        page,
        page_size: 20,
      }),
  });

  const { data: stats } = useQuery({
    queryKey: ['urls-stats'],
    queryFn: () => urls.stats(),
  });

  return (
    <MainLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Discovered URLs</h1>
          <p className="mt-1 text-gray-500">View and manage discovered URLs from scraping</p>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="p-4">
              <p className="text-sm text-gray-500">Total URLs</p>
              <p className="text-2xl font-semibold">{stats.total}</p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-gray-500">Relevant</p>
              <p className="text-2xl font-semibold text-green-600">{stats.relevance?.relevant || 0}</p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-gray-500">Not Relevant</p>
              <p className="text-2xl font-semibold text-gray-600">{stats.relevance?.not_relevant || 0}</p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-gray-500">Verified</p>
              <p className="text-2xl font-semibold text-blue-600">{stats.human_verified || 0}</p>
            </Card>
          </div>
        )}

        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center gap-4">
              <Input
                placeholder="Search URLs..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="max-w-xs"
              />
              <Select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                options={statusOptions}
                className="w-36"
              />
              <Select
                value={relevance}
                onChange={(e) => setRelevance(e.target.value)}
                options={relevanceOptions}
                className="w-36"
              />
              <Select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                options={priorityOptions}
                className="w-32"
              />
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex justify-center py-8">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent"></div>
              </div>
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>URL</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Relevance</TableHead>
                      <TableHead>Priority</TableHead>
                      <TableHead>Page Type</TableHead>
                      <TableHead>Discovered</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {urlsData?.items.map((url) => (
                      <TableRow key={url.id}>
                        <TableCell>
                          <a
                            href={url.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center text-primary-600 hover:underline"
                          >
                            {truncate(url.url_path || url.url, 50)}
                            <ExternalLink className="ml-1 h-3 w-3" />
                          </a>
                        </TableCell>
                        <TableCell>
                          <span
                            className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${getStatusColor(
                              url.status
                            )}`}
                          >
                            {url.status}
                          </span>
                        </TableCell>
                        <TableCell>
                          <span
                            className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${getStatusColor(
                              url.relevance
                            )}`}
                          >
                            {url.relevance}
                          </span>
                        </TableCell>
                        <TableCell>
                          <span
                            className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${getStatusColor(
                              url.priority
                            )}`}
                          >
                            {url.priority}
                          </span>
                        </TableCell>
                        <TableCell>
                          {url.page_type ? <Badge>{url.page_type}</Badge> : '-'}
                        </TableCell>
                        <TableCell>{formatDateTime(url.discovered_at)}</TableCell>
                        <TableCell>
                          <Link href={`/urls/${url.id}`}>
                            <Button size="sm" variant="ghost">
                              <Eye className="h-4 w-4" />
                            </Button>
                          </Link>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {/* Pagination */}
                {urlsData && urlsData.total_pages > 1 && (
                  <div className="mt-4 flex items-center justify-between">
                    <p className="text-sm text-gray-500">
                      Page {page} of {urlsData.total_pages} ({urlsData.total} URLs)
                    </p>
                    <div className="flex space-x-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={page === 1}
                        onClick={() => setPage(page - 1)}
                      >
                        Previous
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={page === urlsData.total_pages}
                        onClick={() => setPage(page + 1)}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}
