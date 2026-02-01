'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import MainLayout from '@/components/layout/MainLayout';
import Card, { CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Badge from '@/components/ui/Badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { items } from '@/lib/api';
import { formatDateTime, getStatusColor, getItemTypeLabel, truncate } from '@/lib/utils';
import type { Item, ItemType, ItemStatus } from '@/types';
import { CheckCircle, Eye, Trash2, Send } from 'lucide-react';
import Link from 'next/link';

const itemTypeOptions = [
  { value: '', label: 'All Types' },
  { value: 'PROGRAM', label: 'Program' },
  { value: 'SCHOLARSHIP', label: 'Scholarship' },
  { value: 'CONFERENCE', label: 'Conference' },
  { value: 'EXCHANGE', label: 'Exchange' },
];

const statusOptions = [
  { value: '', label: 'All Statuses' },
  { value: 'DRAFT', label: 'Draft' },
  { value: 'NEEDS_REVIEW', label: 'Needs Review' },
  { value: 'VERIFIED', label: 'Verified' },
  { value: 'PUBLISHED', label: 'Published' },
  { value: 'OUTDATED', label: 'Outdated' },
  { value: 'ARCHIVED', label: 'Archived' },
];

export default function ItemsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [itemType, setItemType] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);

  const { data: itemsData, isLoading } = useQuery({
    queryKey: ['items', search, itemType, status, page],
    queryFn: () =>
      items.list({
        search: search || undefined,
        item_type: itemType || undefined,
        status: status || undefined,
        page,
        page_size: 20,
      }),
  });

  const verifyMutation = useMutation({
    mutationFn: (id: string) => items.verify(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['items'] });
      toast.success('Item verified');
    },
  });

  const publishMutation = useMutation({
    mutationFn: (id: string) => items.publish(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['items'] });
      toast.success('Item published');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => items.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['items'] });
      toast.success('Item deleted');
    },
  });

  const getItemTitle = (item: Item) => {
    const data = item.data;
    switch (item.item_type) {
      case 'PROGRAM':
        return data.program_name || data.university_name || 'Unnamed Program';
      case 'SCHOLARSHIP':
        return data.scholarship_name || data.provider || 'Unnamed Scholarship';
      case 'CONFERENCE':
        return data.conference_name || data.acronym || 'Unnamed Conference';
      case 'EXCHANGE':
        return data.program_name || data.host_university || 'Unnamed Exchange';
      default:
        return 'Unknown Item';
    }
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Items</h1>
          <p className="mt-1 text-gray-500">Manage extracted items</p>
        </div>

        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center gap-4">
              <Input
                placeholder="Search items..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="max-w-xs"
              />
              <Select
                value={itemType}
                onChange={(e) => setItemType(e.target.value)}
                options={itemTypeOptions}
                className="w-40"
              />
              <Select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                options={statusOptions}
                className="w-40"
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
                      <TableHead>Title</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Confidence</TableHead>
                      <TableHead>Verified</TableHead>
                      <TableHead>Updated</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {itemsData?.items.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell>
                          <Link
                            href={`/items/${item.id}`}
                            className="font-medium text-primary-600 hover:underline"
                          >
                            {truncate(getItemTitle(item), 40)}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <Badge variant="info">{getItemTypeLabel(item.item_type)}</Badge>
                        </TableCell>
                        <TableCell>
                          <span
                            className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${getStatusColor(
                              item.status
                            )}`}
                          >
                            {item.status}
                          </span>
                        </TableCell>
                        <TableCell>
                          {item.extraction_confidence
                            ? `${item.extraction_confidence.toFixed(0)}%`
                            : 'N/A'}
                        </TableCell>
                        <TableCell>
                          {item.human_verified ? (
                            <CheckCircle className="h-5 w-5 text-green-500" />
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </TableCell>
                        <TableCell>{formatDateTime(item.updated_at)}</TableCell>
                        <TableCell>
                          <div className="flex items-center space-x-2">
                            <Link href={`/items/${item.id}`}>
                              <Button size="sm" variant="ghost">
                                <Eye className="h-4 w-4" />
                              </Button>
                            </Link>
                            {!item.human_verified && (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => verifyMutation.mutate(item.id)}
                              >
                                <CheckCircle className="h-4 w-4 text-green-500" />
                              </Button>
                            )}
                            {item.status !== 'PUBLISHED' && (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => publishMutation.mutate(item.id)}
                              >
                                <Send className="h-4 w-4 text-blue-500" />
                              </Button>
                            )}
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                if (confirm('Delete this item?')) {
                                  deleteMutation.mutate(item.id);
                                }
                              }}
                            >
                              <Trash2 className="h-4 w-4 text-red-500" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {/* Pagination */}
                {itemsData && itemsData.total_pages > 1 && (
                  <div className="mt-4 flex items-center justify-between">
                    <p className="text-sm text-gray-500">
                      Page {page} of {itemsData.total_pages} ({itemsData.total} items)
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
                        disabled={page === itemsData.total_pages}
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
