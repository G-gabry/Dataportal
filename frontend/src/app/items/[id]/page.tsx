'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import MainLayout from '@/components/layout/MainLayout';
import Card, { CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Badge from '@/components/ui/Badge';
import { items, schemas } from '@/lib/api';
import { formatDateTime, getStatusColor, getItemTypeLabel } from '@/lib/utils';
import { ArrowLeft, Save, CheckCircle, Send } from 'lucide-react';

export default function ItemDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const itemId = params.id as string;

  const [editedData, setEditedData] = useState<Record<string, any>>({});
  const [notes, setNotes] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  const { data: item, isLoading } = useQuery({
    queryKey: ['item', itemId],
    queryFn: () => items.get(itemId),
    enabled: !!itemId,
  });

  const { data: schema } = useQuery({
    queryKey: ['schema', item?.item_type],
    queryFn: () => schemas.get(item!.item_type),
    enabled: !!item?.item_type,
  });

  const updateMutation = useMutation({
    mutationFn: (data: any) => items.update(itemId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['item', itemId] });
      toast.success('Item updated');
      setIsEditing(false);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update');
    },
  });

  const verifyMutation = useMutation({
    mutationFn: () => items.verify(itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['item', itemId] });
      toast.success('Item verified');
    },
  });

  const publishMutation = useMutation({
    mutationFn: () => items.publish(itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['item', itemId] });
      toast.success('Item published');
    },
  });

  const handleSave = () => {
    updateMutation.mutate({
      data: { ...item?.data, ...editedData },
      notes: notes || item?.notes,
    });
  };

  const handleFieldChange = (field: string, value: any) => {
    setEditedData({ ...editedData, [field]: value });
  };

  const renderField = (fieldName: string, fieldInfo: any, value: any) => {
    const displayValue = editedData[fieldName] ?? value;
    const fieldStatus = item?.field_status?.[fieldName];

    if (!isEditing) {
      return (
        <div key={fieldName} className="border-b py-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-500">{fieldName}</label>
            {fieldStatus && (
              <Badge
                variant={
                  fieldStatus === 'EXTRACTED'
                    ? 'success'
                    : fieldStatus === 'NOT_AVAILABLE'
                    ? 'default'
                    : 'warning'
                }
              >
                {fieldStatus}
              </Badge>
            )}
          </div>
          <p className="mt-1 text-gray-900">
            {displayValue !== null && displayValue !== undefined
              ? Array.isArray(displayValue)
                ? displayValue.join(', ')
                : typeof displayValue === 'object'
                ? JSON.stringify(displayValue)
                : String(displayValue)
              : 'N/A'}
          </p>
        </div>
      );
    }

    // Editing mode
    const type = fieldInfo?.type || 'string';

    if (type === 'boolean') {
      return (
        <div key={fieldName} className="border-b py-3">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={displayValue === true}
              onChange={(e) => handleFieldChange(fieldName, e.target.checked)}
              className="mr-2"
            />
            <span className="text-sm font-medium text-gray-700">{fieldName}</span>
          </label>
        </div>
      );
    }

    if (type === 'array') {
      return (
        <div key={fieldName} className="border-b py-3">
          <label className="text-sm font-medium text-gray-700">{fieldName}</label>
          <Input
            value={Array.isArray(displayValue) ? displayValue.join(', ') : displayValue || ''}
            onChange={(e) =>
              handleFieldChange(
                fieldName,
                e.target.value.split(',').map((s) => s.trim())
              )
            }
            placeholder="Comma-separated values"
            className="mt-1"
          />
        </div>
      );
    }

    if (type === 'text') {
      return (
        <div key={fieldName} className="border-b py-3">
          <label className="text-sm font-medium text-gray-700">{fieldName}</label>
          <textarea
            value={displayValue || ''}
            onChange={(e) => handleFieldChange(fieldName, e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            rows={3}
          />
        </div>
      );
    }

    if (type === 'number') {
      return (
        <div key={fieldName} className="border-b py-3">
          <label className="text-sm font-medium text-gray-700">{fieldName}</label>
          <Input
            type="number"
            value={displayValue || ''}
            onChange={(e) => handleFieldChange(fieldName, parseFloat(e.target.value) || null)}
            className="mt-1"
          />
        </div>
      );
    }

    // Default: string/text input
    return (
      <div key={fieldName} className="border-b py-3">
        <label className="text-sm font-medium text-gray-700">{fieldName}</label>
        <Input
          value={displayValue || ''}
          onChange={(e) => handleFieldChange(fieldName, e.target.value)}
          className="mt-1"
        />
      </div>
    );
  };

  if (isLoading) {
    return (
      <MainLayout>
        <div className="flex justify-center py-8">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent"></div>
        </div>
      </MainLayout>
    );
  }

  if (!item) {
    return (
      <MainLayout>
        <div className="text-center py-8">
          <p className="text-gray-500">Item not found</p>
        </div>
      </MainLayout>
    );
  }

  const schemaFields = schema?.schema_json?.fields || {};

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button variant="ghost" onClick={() => router.back()}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {item.data.program_name ||
                  item.data.scholarship_name ||
                  item.data.conference_name ||
                  item.data.name ||
                  'Item Details'}
              </h1>
              <div className="mt-1 flex items-center space-x-2">
                <Badge variant="info">{getItemTypeLabel(item.item_type)}</Badge>
                <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${getStatusColor(item.status)}`}>
                  {item.status}
                </span>
                {item.human_verified && (
                  <Badge variant="success">Verified</Badge>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {isEditing ? (
              <>
                <Button variant="secondary" onClick={() => setIsEditing(false)}>
                  Cancel
                </Button>
                <Button onClick={handleSave} isLoading={updateMutation.isPending}>
                  <Save className="mr-2 h-4 w-4" />
                  Save
                </Button>
              </>
            ) : (
              <>
                <Button variant="secondary" onClick={() => setIsEditing(true)}>
                  Edit
                </Button>
                {!item.human_verified && (
                  <Button
                    variant="secondary"
                    onClick={() => verifyMutation.mutate()}
                    isLoading={verifyMutation.isPending}
                  >
                    <CheckCircle className="mr-2 h-4 w-4" />
                    Verify
                  </Button>
                )}
                {item.status !== 'PUBLISHED' && (
                  <Button onClick={() => publishMutation.mutate()} isLoading={publishMutation.isPending}>
                    <Send className="mr-2 h-4 w-4" />
                    Publish
                  </Button>
                )}
              </>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Extracted Data</CardTitle>
              </CardHeader>
              <CardContent>
                {Object.entries(schemaFields).map(([fieldName, fieldInfo]) =>
                  renderField(fieldName, fieldInfo, item.data[fieldName])
                )}

                {/* Custom fields */}
                {item.custom_fields && Object.keys(item.custom_fields).length > 0 && (
                  <div className="mt-6">
                    <h4 className="text-sm font-semibold text-gray-700 mb-2">Custom Fields</h4>
                    {Object.entries(item.custom_fields).map(([key, value]) => (
                      <div key={key} className="border-b py-2">
                        <label className="text-sm font-medium text-gray-500">{key}</label>
                        <p className="mt-1 text-gray-900">{String(value)}</p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Notes */}
            <Card>
              <CardHeader>
                <CardTitle>Notes</CardTitle>
              </CardHeader>
              <CardContent>
                {isEditing ? (
                  <textarea
                    value={notes || item.notes || ''}
                    onChange={(e) => setNotes(e.target.value)}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                    rows={4}
                    placeholder="Add notes..."
                  />
                ) : (
                  <p className="text-gray-700">{item.notes || 'No notes'}</p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Metadata</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-gray-500">Extraction Confidence</label>
                  <p className="text-gray-900">
                    {item.extraction_confidence ? `${item.extraction_confidence.toFixed(0)}%` : 'N/A'}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Human Edited</label>
                  <p className="text-gray-900">{item.human_edited ? 'Yes' : 'No'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Extracted At</label>
                  <p className="text-gray-900">{formatDateTime(item.extracted_at)}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Last Updated</label>
                  <p className="text-gray-900">{formatDateTime(item.updated_at)}</p>
                </div>
                {item.verified_at && (
                  <div>
                    <label className="text-sm font-medium text-gray-500">Verified At</label>
                    <p className="text-gray-900">{formatDateTime(item.verified_at)}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {item.tags && item.tags.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Tags</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {item.tags.map((tag) => (
                      <Badge key={tag}>{tag}</Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
