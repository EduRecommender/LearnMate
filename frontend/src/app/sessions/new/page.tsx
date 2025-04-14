'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import AppLayout from '@/components/layout/AppLayout';
import { useAuth } from '@/lib/auth';

const timeCommitmentOptions = [
  { value: '1-2 hours', label: '1-2 hours per week' },
  { value: '3-5 hours', label: '3-5 hours per week' },
  { value: '6-10 hours', label: '6-10 hours per week' },
  { value: '10+ hours', label: '10+ hours per week' },
];

const difficultyLevelOptions = [
  { value: 'beginner', label: 'Beginner' },
  { value: 'intermediate', label: 'Intermediate' },
  { value: 'advanced', label: 'Advanced' },
];

export default function NewSessionPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [formData, setFormData] = useState({
    name: '',
    field_of_study: '',
    study_goal: '',
    context: '',
    study_days: '',
    hours_per_day: '',
    difficulty_level: '',
  });
  const [error, setError] = useState<string | null>(null);

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/auth/login');
    }
  }, [authLoading, isAuthenticated, router]);

  const createSessionMutation = useMutation({
    mutationFn: (data: any) => apiClient.sessions.create(data),
    onSuccess: async () => {
      // Invalidate and refetch sessions query
      await queryClient.invalidateQueries({ queryKey: ['sessions'] });
      router.push('/dashboard');
    },
    onError: (error: any) => {
      console.error('Failed to create session:', error);
      setError(error.response?.data?.detail || 'Failed to create session');
    }
  });

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);

    try {
      const formattedData = {
        name: formData.name,
        field_of_study: formData.field_of_study,
        study_goal: formData.study_goal,
        context: formData.context,
        time_commitment: parseFloat(formData.hours_per_day) * parseInt(formData.study_days),
        difficulty_level: formData.difficulty_level,
        preferences: {},
        progress: {},
        syllabus: {}
      };
      
      await createSessionMutation.mutateAsync(formattedData);
    } catch (err: any) {
      console.error('Error creating session:', err);
      setError(err.response?.data?.detail || 'Error creating session.');
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  if (authLoading) {
    return (
      <AppLayout>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      </AppLayout>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <AppLayout>
      <div className="max-w-2xl mx-auto py-8">
        <h1 className="text-2xl font-semibold text-gray-900 mb-6">Create New Study Session</h1>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700">
              Session Name
            </label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
            />
          </div>

          <div>
            <label htmlFor="field_of_study" className="block text-sm font-medium text-gray-700">
              Field of Study
            </label>
            <input
              type="text"
              id="field_of_study"
              name="field_of_study"
              value={formData.field_of_study}
              onChange={handleChange}
              required
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
            />
          </div>

          <div>
            <label htmlFor="study_goal" className="block text-sm font-medium text-gray-700">
              Study Goal
            </label>
            <textarea
              id="study_goal"
              name="study_goal"
              value={formData.study_goal}
              onChange={handleChange}
              required
              rows={3}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
            />
          </div>

          <div>
            <label htmlFor="context" className="block text-sm font-medium text-gray-700">
              Context
            </label>
            <textarea
              id="context"
              name="context"
              value={formData.context}
              onChange={handleChange}
              required
              rows={3}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
            />
          </div>

          <div>
            <label htmlFor="study_days" className="block text-sm font-medium text-gray-700">
              Number of Study Days
            </label>
            <input
              type="number"
              id="study_days"
              name="study_days"
              min="1"
              max="7"
              value={formData.study_days}
              onChange={handleChange}
              required
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
            />
          </div>

          <div>
            <label htmlFor="hours_per_day" className="block text-sm font-medium text-gray-700">
              Hours per Day
            </label>
            <input
              type="number"
              id="hours_per_day"
              name="hours_per_day"
              min="1"
              max="24"
              value={formData.hours_per_day}
              onChange={handleChange}
              required
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
            />
          </div>

          <div>
            <label htmlFor="difficulty_level" className="block text-sm font-medium text-gray-700">
              Difficulty Level
            </label>
            <select
              id="difficulty_level"
              name="difficulty_level"
              value={formData.difficulty_level}
              onChange={handleChange}
              required
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
            >
              <option value="">Select difficulty level</option>
              {difficultyLevelOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex justify-end space-x-4">
            <button
              type="button"
              onClick={() => router.back()}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createSessionMutation.isPending}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {createSessionMutation.isPending ? 'Creating...' : 'Create Session'}
            </button>
          </div>
        </form>
      </div>
    </AppLayout>
  );
} 