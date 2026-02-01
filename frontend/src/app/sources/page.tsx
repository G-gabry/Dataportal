'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import MainLayout from '@/components/layout/MainLayout';
import Card, { CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Modal from '@/components/ui/Modal';
import Badge from '@/components/ui/Badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { sources } from '@/lib/api';
import { formatDateTime, getSourceTypeLabel, truncate } from '@/lib/utils';
import type { Source, SourceType, ItemType } from '@/types';
import { Plus, Play, Edit, Trash2, Star, ExternalLink } from 'lucide-react';

const sourceTypeOptions = [
  { value: 'UNIVERSITY', label: 'University' },
  { value: 'SCHOLARSHIP_ORG', label: 'Scholarship Organization' },
  { value: 'CONFERENCE_ORG', label: 'Conference Organization' },
  { value: 'EXCHANGE_ORG', label: 'Exchange Organization' },
  { value: 'OTHER', label: 'Other' },
];

const itemTypeOptions = [
  { value: 'PROGRAM', label: 'Program' },
  { value: 'SCHOLARSHIP', label: 'Scholarship' },
  { value: 'CONFERENCE', label: 'Conference' },
  { value: 'EXCHANGE', label: 'Exchange' },
];

export default function SourcesPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSource, setEditingSource] = useState<Source | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    type: 'UNIVERSITY' as SourceType,
    base_url: '',
    target_item_types: ['PROGRAM'] as ItemType[],
    is_important: false,
    notes: '',
  });

  const { data: sourcesData, isLoading } = useQuery({
    queryKey: ['sources', search],
    queryFn: () => sources.list({ search, page_size: 100 }),
  });

  const createMutation = useMutation({
    mutationFn: (data: Partial<Source>) => sources.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] });
      toast.success('Source created successfully');
      closeModal();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create source');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Source> }) =>
      sources.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] });
      toast.success('Source updated successfully');
      closeModal();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update source');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => sources.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] });
      toast.success('Source deleted successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete source');
    },
  });

  const scrapeMutation = useMutation({
    mutationFn: (id: string) => sources.scrape(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success('Scrape job started');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to start scrape job');
    },
  });

  const openCreateModal = () => {
    setEditingSource(null);
    setFormData({
      name: '',
      type: 'UNIVERSITY',
      base_url: '',
      target_item_types: ['PROGRAM'],
      is_important: false,
      notes: '',
    });
    setIsModalOpen(true);
  };

  const openEditModal = (source: Source) => {
    setEditingSource(source);
    setFormData({
      name: source.name,
      type: source.type,
      base_url: source.base_url,
      target_item_types: source.target_item_types,
      is_important: source.is_important,
      notes: source.notes || '',
    });
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingSource(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingSource) {
      updateMutation.mutate({ id: editingSource.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleDelete = (source: Source) => {
    if (confirm(`Are you sure you want to delete "${source.name}"?`)) {
      deleteMutation.mutate(source.id);
    }
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Sources</h1>
            <p className="mt-1 text-gray-500">Manage data sources for scraping</p>
          </div>
          <Button onClick={openCreateModal}>
            <Plus className="mr-2 h-4 w-4" />
            Add Source
          </Button>
        </div>

        <Card>
          <CardHeader>
            <Input
              placeholder="Search sources..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="max-w-sm"
            />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex justify-center py-8">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent"></div>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>URL</TableHead>
                    <TableHead>Items</TableHead>
                    <TableHead>Last Scraped</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sourcesData?.items.map((source) => (
                    <TableRow key={source.id}>
                      <TableCell>
                        <div className="flex items-center">
                          {source.is_important && (
                            <Star className="mr-2 h-4 w-4 text-yellow-500" />
                          )}
                          <span className="font-medium">{source.name}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge>{getSourceTypeLabel(source.type)}</Badge>
                      </TableCell>
                      <TableCell>
                        <a
                          href={source.base_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center text-primary-600 hover:underline"
                        >
                          {truncate(source.base_url, 30)}
                          <ExternalLink className="ml-1 h-3 w-3" />
                        </a>
                      </TableCell>
                      <TableCell>
                        <span className="font-semibold">{source.items_extracted_count}</span>
                        <span className="text-gray-500"> / {source.urls_discovered_count} URLs</span>
                      </TableCell>
                      <TableCell>{formatDateTime(source.last_scraped_at)}</TableCell>
                      <TableCell>
                        <Badge variant={source.is_active ? 'success' : 'default'}>
                          {source.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => scrapeMutation.mutate(source.id)}
                            disabled={!source.is_active}
                          >
                            <Play className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => openEditModal(source)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDelete(source)}
                          >
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Create/Edit Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={closeModal}
        title={editingSource ? 'Edit Source' : 'Add Source'}
        size="lg"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="e.g., Massachusetts Institute of Technology"
            required
          />

          <Select
            label="Type"
            value={formData.type}
            onChange={(e) => setFormData({ ...formData, type: e.target.value as SourceType })}
            options={sourceTypeOptions}
          />

          <Input
            label="Base URL"
            value={formData.base_url}
            onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
            placeholder="https://example.edu"
            required
          />

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Target Item Types
            </label>
            <div className="flex flex-wrap gap-2">
              {itemTypeOptions.map((option) => (
                <label key={option.value} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.target_item_types.includes(option.value as ItemType)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setFormData({
                          ...formData,
                          target_item_types: [...formData.target_item_types, option.value as ItemType],
                        });
                      } else {
                        setFormData({
                          ...formData,
                          target_item_types: formData.target_item_types.filter(
                            (t) => t !== option.value
                          ),
                        });
                      }
                    }}
                    className="mr-2"
                  />
                  {option.label}
                </label>
              ))}
            </div>
          </div>

          <label className="flex items-center">
            <input
              type="checkbox"
              checked={formData.is_important}
              onChange={(e) => setFormData({ ...formData, is_important: e.target.checked })}
              className="mr-2"
            />
            Mark as Important (prioritize for updates)
          </label>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Notes</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              rows={3}
              placeholder="Optional notes about this source..."
            />
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <Button type="button" variant="secondary" onClick={closeModal}>
              Cancel
            </Button>
            <Button
              type="submit"
              isLoading={createMutation.isPending || updateMutation.isPending}
            >
              {editingSource ? 'Update' : 'Create'}
            </Button>
          </div>
        </form>
      </Modal>
    </MainLayout>
  );
}
