'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import MainLayout from '@/components/layout/MainLayout';
import Card, { CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Select from '@/components/ui/Select';
import Badge from '@/components/ui/Badge';
import { items } from '@/lib/api';
import { getItemTypeLabel, getStatusColor, truncate } from '@/lib/utils';
import { CheckCircle, Send, Eye, ChevronRight } from 'lucide-react';
import Link from 'next/link';

const itemTypeOptions = [
  { value: '', label: 'All Types' },
  { value: 'PROGRAM', label: 'Program' },
  { value: 'SCHOLARSHIP', label: 'Scholarship' },
  { value: 'CONFERENCE', label: 'Conference' },
  { value: 'EXCHANGE', label: 'Exchange' },
];

export default function ReviewQueuePage() {
  const queryClient = useQueryClient();
  const [itemType, setItemType] = useState('');
  const [page, setPage] = useState(1);

  const { data: reviewData, isLoading } = useQuery({
    queryKey: ['review-queue', itemType, page],
    queryFn: () =>
      items.reviewQueue({
        item_type: itemType || undefined,
        page,
        page_size: 10,
      }),
  });

  const verifyMutation = useMutation({
    mutationFn: (id: string) => items.verify(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-queue'] });
      toast.success('Item verified');
    },
  });

  const publishMutation = useMutation({
    mutationFn: (id: string) => items.publish(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-queue'] });
      toast.success('Item published');
    },
  });

  const getItemTitle = (item: any) => {
    const data = item.data;
    return (
      data.program_name ||
      data.scholarship_name ||
      data.conference_name ||
      data.name ||
      'Unnamed Item'
    );
  };

  const getConfidenceColor = (confidence: number | null) => {
    if (!confidence) return 'text-gray-500';
    if (confidence >= 80) return 'text-green-600';
    if (confidence >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Review Queue</h1>
            <p className="mt-1 text-gray-500">
              Items that need human review before publishing
            </p>
          </div>
          <Select
            value={itemType}
            onChange={(e) => setItemType(e.target.value)}
            options={itemTypeOptions}
            className="w-40"
          />
        </div>

        {isLoading ? (
          <div className="flex justify-center py-8">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent"></div>
          </div>
        ) : reviewData?.items.length === 0 ? (
          <Card className="py-12 text-center">
            <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">All caught up!</h3>
            <p className="mt-2 text-gray-500">No items pending review</p>
          </Card>
        ) : (
          <div className="space-y-4">
            {reviewData?.items.map((item) => (
              <Card key={item.id}>
                <div className="flex items-start justify-between p-6">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <Badge variant="info">{getItemTypeLabel(item.item_type)}</Badge>
                      <span
                        className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${getStatusColor(
                          item.status
                        )}`}
                      >
                        {item.status}
                      </span>
                      <span
                        className={`text-sm font-medium ${getConfidenceColor(
                          item.extraction_confidence
                        )}`}
                      >
                        {item.extraction_confidence
                          ? `${item.extraction_confidence.toFixed(0)}% confidence`
                          : 'No confidence score'}
                      </span>
                    </div>

                    <h3 className="mt-2 text-lg font-medium text-gray-900">
                      {truncate(getItemTitle(item), 60)}
                    </h3>

                    {/* Preview of key fields */}
                    <div className="mt-3 grid grid-cols-2 gap-4 text-sm">
                      {Object.entries(item.data)
                        .slice(0, 4)
                        .map(([key, value]) => (
                          <div key={key}>
                            <span className="text-gray-500">{key}: </span>
                            <span className="text-gray-900">
                              {truncate(
                                value !== null && value !== undefined
                                  ? Array.isArray(value)
                                    ? value.join(', ')
                                    : String(value)
                                  : 'N/A',
                                30
                              )}
                            </span>
                          </div>
                        ))}
                    </div>

                    {/* Field status warnings */}
                    {item.field_status && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {Object.entries(item.field_status)
                          .filter(([_, status]) => status === 'UNKNOWN')
                          .slice(0, 3)
                          .map(([field]) => (
                            <Badge key={field} variant="warning">
                              {field}: Unknown
                            </Badge>
                          ))}
                      </div>
                    )}
                  </div>

                  <div className="ml-6 flex flex-col items-end space-y-2">
                    <Link href={`/items/${item.id}`}>
                      <Button variant="secondary" size="sm">
                        <Eye className="mr-2 h-4 w-4" />
                        Review
                        <ChevronRight className="ml-1 h-4 w-4" />
                      </Button>
                    </Link>

                    <div className="flex space-x-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => verifyMutation.mutate(item.id)}
                        isLoading={verifyMutation.isPending}
                      >
                        <CheckCircle className="mr-1 h-4 w-4 text-green-500" />
                        Verify
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => publishMutation.mutate(item.id)}
                        isLoading={publishMutation.isPending}
                      >
                        <Send className="mr-1 h-4 w-4" />
                        Publish
                      </Button>
                    </div>
                  </div>
                </div>
              </Card>
            ))}

            {/* Pagination */}
            {reviewData && reviewData.total_pages > 1 && (
              <div className="flex items-center justify-between pt-4">
                <p className="text-sm text-gray-500">
                  Page {page} of {reviewData.total_pages} ({reviewData.total} items)
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
                    disabled={page === reviewData.total_pages}
                    onClick={() => setPage(page + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </MainLayout>
  );
}
