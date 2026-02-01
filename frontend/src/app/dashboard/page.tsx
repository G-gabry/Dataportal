'use client';

import { useQuery } from '@tanstack/react-query';
import MainLayout from '@/components/layout/MainLayout';
import Card, { CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { sources, items, jobs, urls } from '@/lib/api';
import { formatCurrency, getStatusColor } from '@/lib/utils';
import {
  Database,
  FileText,
  Link2,
  Activity,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Clock,
} from 'lucide-react';

export default function DashboardPage() {
  const { data: sourcesData } = useQuery({
    queryKey: ['sources-list'],
    queryFn: () => sources.list({ page_size: 100 }),
  });

  const { data: itemStats } = useQuery({
    queryKey: ['items-stats'],
    queryFn: () => items.stats(),
  });

  const { data: jobStats } = useQuery({
    queryKey: ['jobs-stats'],
    queryFn: () => jobs.stats(),
  });

  const { data: urlStats } = useQuery({
    queryKey: ['urls-stats'],
    queryFn: () => urls.stats(),
  });

  const { data: recentJobs } = useQuery({
    queryKey: ['recent-jobs'],
    queryFn: () => jobs.list({ page_size: 5 }),
  });

  const statCards = [
    {
      title: 'Total Sources',
      value: sourcesData?.total || 0,
      icon: Database,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      title: 'Total Items',
      value: itemStats?.total || 0,
      icon: FileText,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
    {
      title: 'URLs Discovered',
      value: urlStats?.total || 0,
      icon: Link2,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
    },
    {
      title: 'Total Jobs',
      value: jobStats?.total_jobs || 0,
      icon: Activity,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
    },
  ];

  return (
    <MainLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-1 text-gray-500">Overview of your data portal</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          {statCards.map((stat) => (
            <Card key={stat.title}>
              <div className="flex items-center">
                <div className={`rounded-lg p-3 ${stat.bgColor}`}>
                  <stat.icon className={`h-6 w-6 ${stat.color}`} />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">{stat.title}</p>
                  <p className="text-2xl font-semibold text-gray-900">{stat.value}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* Items by Type & Cost Summary */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Items by Type</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {itemStats?.by_type &&
                  Object.entries(itemStats.by_type).map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">{type}</span>
                      <span className="font-semibold text-gray-900">{count as number}</span>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Cost Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Total AI Cost</span>
                  <span className="font-semibold text-gray-900">
                    {formatCurrency(jobStats?.total_cost_usd || 0)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Total Tokens Used</span>
                  <span className="font-semibold text-gray-900">
                    {(jobStats?.total_tokens || 0).toLocaleString()}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Firecrawl Calls</span>
                  <span className="font-semibold text-gray-900">
                    {(jobStats?.total_firecrawl_calls || 0).toLocaleString()}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Items Extracted</span>
                  <span className="font-semibold text-gray-900">
                    {(jobStats?.total_items_extracted || 0).toLocaleString()}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Jobs */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            {recentJobs?.items && recentJobs.items.length > 0 ? (
              <div className="space-y-4">
                {recentJobs.items.map((job) => (
                  <div
                    key={job.id}
                    className="flex items-center justify-between rounded-lg border p-4"
                  >
                    <div className="flex items-center space-x-4">
                      <div
                        className={`rounded-full p-2 ${
                          job.status === 'COMPLETED'
                            ? 'bg-green-100'
                            : job.status === 'RUNNING'
                            ? 'bg-blue-100'
                            : job.status === 'FAILED'
                            ? 'bg-red-100'
                            : 'bg-gray-100'
                        }`}
                      >
                        {job.status === 'COMPLETED' ? (
                          <CheckCircle className="h-5 w-5 text-green-600" />
                        ) : job.status === 'RUNNING' ? (
                          <Clock className="h-5 w-5 text-blue-600" />
                        ) : job.status === 'FAILED' ? (
                          <AlertCircle className="h-5 w-5 text-red-600" />
                        ) : (
                          <Clock className="h-5 w-5 text-gray-600" />
                        )}
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{job.job_type}</p>
                        <p className="text-sm text-gray-500">
                          {job.items_extracted} items extracted
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span
                        className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${getStatusColor(
                          job.status
                        )}`}
                      >
                        {job.status}
                      </span>
                      <p className="mt-1 text-sm text-gray-500">
                        {job.progress_percent}% complete
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center text-gray-500">No recent jobs</p>
            )}
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}
