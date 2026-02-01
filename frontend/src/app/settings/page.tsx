'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import MainLayout from '@/components/layout/MainLayout';
import Card, { CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Select from '@/components/ui/Select';
import { settings } from '@/lib/api';
import { useState, useEffect } from 'react';
import { Save, RefreshCw } from 'lucide-react';

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [selectedProvider, setSelectedProvider] = useState('');
  const [selectedModel, setSelectedModel] = useState('');

  const { data: aiConfig, isLoading } = useQuery({
    queryKey: ['ai-config'],
    queryFn: () => settings.getAIConfig(),
  });

  const { data: availableModels } = useQuery({
    queryKey: ['available-models'],
    queryFn: () => settings.getAvailableModels(),
  });

  useEffect(() => {
    if (aiConfig) {
      setSelectedProvider(aiConfig.default_provider);
      setSelectedModel(aiConfig.default_model);
    }
  }, [aiConfig]);

  const updateMutation = useMutation({
    mutationFn: (data: any) => settings.updateAIConfig(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-config'] });
      toast.success('Settings updated');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update settings');
    },
  });

  const handleSave = () => {
    updateMutation.mutate({
      default_provider: selectedProvider,
      default_model: selectedModel,
    });
  };

  const providerOptions = aiConfig
    ? Object.keys(aiConfig.providers).map((p) => ({ value: p, label: p.charAt(0).toUpperCase() + p.slice(1) }))
    : [];

  const modelOptions =
    aiConfig && selectedProvider
      ? aiConfig.providers[selectedProvider]?.models.map((m) => ({ value: m, label: m })) || []
      : [];

  if (isLoading) {
    return (
      <MainLayout>
        <div className="flex justify-center py-8">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent"></div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="mt-1 text-gray-500">Configure AI providers and system settings</p>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* AI Configuration */}
          <Card>
            <CardHeader>
              <CardTitle>AI Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Default Provider
                </label>
                <Select
                  value={selectedProvider}
                  onChange={(e) => {
                    setSelectedProvider(e.target.value);
                    // Reset model when provider changes
                    const providerModels = aiConfig?.providers[e.target.value]?.models;
                    if (providerModels && providerModels.length > 0) {
                      setSelectedModel(providerModels[0]);
                    }
                  }}
                  options={providerOptions}
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Default Model
                </label>
                <Select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  options={modelOptions}
                />
              </div>

              <Button onClick={handleSave} isLoading={updateMutation.isPending}>
                <Save className="mr-2 h-4 w-4" />
                Save Changes
              </Button>
            </CardContent>
          </Card>

          {/* Available Models */}
          <Card>
            <CardHeader>
              <CardTitle>Available Models</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {availableModels?.models.map((model) => (
                  <div
                    key={`${model.provider}-${model.model}`}
                    className={`flex items-center justify-between rounded-lg border p-3 ${
                      model.is_default ? 'border-primary-500 bg-primary-50' : 'border-gray-200'
                    }`}
                  >
                    <div>
                      <p className="font-medium text-gray-900">{model.model}</p>
                      <p className="text-sm text-gray-500">{model.provider}</p>
                    </div>
                    {model.is_default && (
                      <span className="rounded-full bg-primary-500 px-2 py-1 text-xs font-medium text-white">
                        Default
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Task Configuration */}
          <Card>
            <CardHeader>
              <CardTitle>Task Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              {aiConfig?.task_config && (
                <div className="space-y-4">
                  {Object.entries(aiConfig.task_config).map(([task, config]) => (
                    <div key={task} className="rounded-lg border border-gray-200 p-3">
                      <p className="font-medium text-gray-900">{task.replace('_', ' ').toUpperCase()}</p>
                      <div className="mt-2 text-sm text-gray-500">
                        <p>Provider: {config.provider}</p>
                        <p>Model: {config.model}</p>
                        {config.batch_size && <p>Batch Size: {config.batch_size}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Model Pricing Info */}
          <Card>
            <CardHeader>
              <CardTitle>Model Pricing (per 1M tokens)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between border-b pb-2">
                  <span className="font-medium">Model</span>
                  <span className="font-medium">Input / Output</span>
                </div>
                <div className="flex justify-between">
                  <span>Claude 3.5 Haiku</span>
                  <span className="text-gray-500">$0.25 / $1.25</span>
                </div>
                <div className="flex justify-between">
                  <span>Claude 3.5 Sonnet</span>
                  <span className="text-gray-500">$3.00 / $15.00</span>
                </div>
                <div className="flex justify-between">
                  <span>Gemini 1.5 Flash</span>
                  <span className="text-gray-500">$0.075 / $0.30</span>
                </div>
                <div className="flex justify-between">
                  <span>Gemini 1.5 Pro</span>
                  <span className="text-gray-500">$1.25 / $5.00</span>
                </div>
                <div className="flex justify-between">
                  <span>GPT-4o Mini</span>
                  <span className="text-gray-500">$0.15 / $0.60</span>
                </div>
                <div className="flex justify-between">
                  <span>GPT-4o</span>
                  <span className="text-gray-500">$2.50 / $10.00</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
}
