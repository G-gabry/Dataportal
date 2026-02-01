'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import MainLayout from '@/components/layout/MainLayout';
import Card, { CardHeader, CardContent } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Select from '@/components/ui/Select';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { jobs } from '@/lib/api';
import { formatDateTime, formatCurrency, getStatusColor } from '@/lib/utils';
import { XCircle, Eye, RefreshCw } from 'lucide-react';

const statusOptions = [
  { value: '', label: 'All Statuses' },
  { value: 'PENDING', label: 'Pending' },
  { value: 'RUNNING', label: 'Running' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'FAILED', label: 'Failed' },
  { value: 'CANCELLED', label: 'Cancelled' },
];

export default function JobsPage() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);

  const { data: jobsData, isLoading, refetch } = useQuery({
    queryKey: ['jobs', status, page],
    queryFn: () =>
      jobs.list({
        status: status || undefined,
        page,
        page_size: 20,
      }),
    refetchInterval: 5000, // Auto-refresh every 5 seconds
  });

  const { data: stats } = useQuery({
    queryKey: ['jobs-stats'],
    queryFn: () => jobs.stats(),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => jobs.cancel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success('Job cancelled');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to cancel job');
    },
  });

  return (
    <MainLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Scrape Jobs</h1>
            <p className="mt-1 text-gray-500">Monitor and manage scraping jobs</p>
          </div>
          <Button variant="secondary" onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="p-4">
              <p className="text-sm text-gray-500">Total Jobs</p>
              <p className="text-2xl font-semibold">{stats.total_jobs}</p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-gray-500">Total Cost</p>
              <p className="text-2xl font-semibold">{formatCurrency(stats.total_cost_usd)}</p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-gray-500">Running</p>
              <p className="text-2xl font-semibold text-blue-600">{stats.by_status?.RUNNING || 0}</p>
            </Card>
            <Card className="p-4">
              <p className="text-sm text-gray-500">Completed</p>
              <p className="text-2xl font-semibold text-green-600">{stats.by_status?.COMPLETED || 0}</p>
            </Card>
          </div>
        )}

        <Card>
          <CardHeader>
            <Select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              options={statusOptions}
              className="w-40"
            />
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
                      <TableHead>Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Progress</TableHead>
                      <TableHead>URLs</TableHead>
                      <TableHead>Items</TableHead>
                      <TableHead>Cost</TableHead>
                      <TableHead>Started</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {jobsData?.items.map((job) => (
                      <TableRow key={job.id}>
                        <TableCell className="font-medium">{job.job_type}</TableCell>
                        <TableCell>
                          <span
                            className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${getStatusColor(
                              job.status
                            )}`}
                          >
                            {job.status}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center space-x-2">
                            <div className="h-2 w-24 overflow-hidden rounded-full bg-gray-200">
                              <div
                                className="h-full bg-primary-500 transition-all"
                                style={{ width: `${job.progress_percent}%` }}
                              />
                            </div>
                            <span className="text-sm text-gray-500">{job.progress_percent}%</span>
                          </div>
                          {job.current_step && (
                            <p className="mt-1 text-xs text-gray-500">{job.current_step}</p>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">
                            <p>{job.urls_discovered} discovered</p>
                            <p className="text-gray-500">{job.urls_relevant} relevant</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className="font-semibold">{job.items_extracted}</span>
                        </TableCell>
                        <TableCell>{formatCurrency(job.ai_cost_usd)}</TableCell>
                        <TableCell>{formatDateTime(job.started_at)}</TableCell>
                        <TableCell>
                          <div className="flex items-center space-x-2">
                            {(job.status === 'PENDING' || job.status === 'RUNNING') && (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => cancelMutation.mutate(job.id)}
                              >
                                <XCircle className="h-4 w-4 text-red-500" />
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {/* Pagination */}
                {jobsData && jobsData.total_pages > 1 && (
                  <div className="mt-4 flex items-center justify-between">
                    <p className="text-sm text-gray-500">
                      Page {page} of {jobsData.total_pages}
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
                        disabled={page === jobsData.total_pages}
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
