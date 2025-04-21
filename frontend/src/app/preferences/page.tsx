'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import AppLayout from '@/components/layout/AppLayout';

const ACADEMIC_LEVELS = [
  'Not Set',
  'High School',
  'Undergraduate',
  'Graduate',
  'PhD',
  'Professional',
  'Other',
];

const GRADE_LEVELS = [
  'Not Set',
  'Freshman',
  'Sophomore',
  'Junior',
  'Senior',
  'Graduate Student',
  'PhD Candidate',
  'Other',
];

const SUBJECT_INTERESTS = [
  'Computer Science',
  'Mathematics',
  'Physics',
  'Chemistry',
  'Biology',
  'Engineering',
  'Business',
  'Arts',
  'Humanities',
  'Social Sciences',
  'Other',
];

const LEARNING_STYLES = [
  'Visual',
  'Auditory',
  'Reading/Writing',
  'Kinesthetic',
  'Social',
  'Solitary',
  'Logical',
  'Verbal',
];

const STUDY_METHODS = [
  'Video Lectures',
  'Reading Textbooks',
  'Practice Exercises',
  'Group Discussions',
  'Flashcards',
  'Mind Maps',
  'Summaries',
  'Online Courses',
  'Interactive Tutorials',
  'Lab Work',
  'Case Studies',
  'Project-based Learning',
];

const DIFFICULTY_LEVELS = ['Not Set', 'Beginner', 'Intermediate', 'Advanced'];

const TIME_AVAILABILITY = [
  'Not Set',
  '1-2 hours',
  '3-5 hours',
  '6-10 hours',
  '11+ hours',
];

const SCHEDULE_TYPES = ['Not Set', 'Flexible', 'Structured', 'Intensive'];

export default function PreferencesPage() {
  const router = useRouter();
  const { user, updatePreferences, error, isLoading } = useAuth();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    level: 'Not Set',
    grade_level: 'Not Set',
    major: '',
    subject_interest: [] as string[],
    learning_styles: [] as string[],
    preferred_study_methods: [] as string[],
    preferred_difficulty: 'Not Set',
    time_available_per_week: 'Not Set',
    preferred_schedule: 'Not Set',
    additional_notes: '',
    has_set_preferences: false,
    has_skipped_preferences: false,
  });

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/auth/login');
    } else if (user?.preferences) {
      setFormData(user.preferences);
    }
  }, [user, isLoading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      console.log('Starting preferences update...');
      console.log('Current form data:', formData);
      setSuccessMessage(null);
      const updatedPreferences = {
        ...formData,
        has_set_preferences: true,
        has_skipped_preferences: false,
      };
      console.log('Sending preferences update with data:', updatedPreferences);
      await updatePreferences(updatedPreferences);
      setSuccessMessage('Preferences saved successfully!');
      console.log('Success message set, waiting before redirect...');
      // Wait for 3 seconds before redirecting
      setTimeout(() => {
        console.log('Redirecting to sessions page...');
        setSuccessMessage(null);
        router.push('/sessions');
      }, 3000);
    } catch (error) {
      console.error('Error in handleSubmit:', error);
      // Error is handled by the auth store
    }
  };

  const handleSkip = async () => {
    try {
      console.log('Starting preferences skip...');
      console.log('Current form data:', formData);
      setSuccessMessage(null);
      const updatedPreferences = {
        ...formData,
        has_set_preferences: true,
        has_skipped_preferences: true,
      };
      console.log('Sending preferences skip with data:', updatedPreferences);
      await updatePreferences(updatedPreferences);
      setSuccessMessage('Preferences skipped successfully!');
      console.log('Success message set, waiting before redirect...');
      // Wait for 3 seconds before redirecting
      setTimeout(() => {
        console.log('Redirecting to sessions page...');
        setSuccessMessage(null);
        router.push('/sessions');
      }, 3000);
    } catch (error) {
      console.error('Error in handleSkip:', error);
      // Error is handled by the auth store
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleMultiSelect = (
    e: React.ChangeEvent<HTMLSelectElement>,
    field: keyof typeof formData
  ) => {
    const values = Array.from(e.target.selectedOptions, (option) => option.value);
    setFormData((prev) => ({
      ...prev,
      [field]: values,
    }));
  };

  if (isLoading) {
    return (
      <AppLayout>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      </AppLayout>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">Learning Preferences</h1>

          <form onSubmit={handleSubmit} className="space-y-8">
            {/* Personal Information */}
            <div className="bg-white shadow px-4 py-5 sm:rounded-lg sm:p-6">
              <div className="md:grid md:grid-cols-3 md:gap-6">
                <div className="md:col-span-1">
                  <h3 className="text-lg font-medium leading-6 text-gray-900">
                    Personal Information
                  </h3>
                  <p className="mt-1 text-sm text-gray-500">
                    Tell us about yourself to help personalize your learning experience.
                  </p>
                </div>
                <div className="mt-5 md:mt-0 md:col-span-2 space-y-4">
                  <div>
                    <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                      Your Name (Optional)
                    </label>
                    <input
                      type="text"
                      name="name"
                      id="name"
                      value={formData.name}
                      onChange={handleChange}
                      className="mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md"
                    />
                  </div>

                  <div>
                    <label htmlFor="level" className="block text-sm font-medium text-gray-700">
                      Academic Level
                    </label>
                    <select
                      id="level"
                      name="level"
                      value={formData.level}
                      onChange={handleChange}
                      className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    >
                      {ACADEMIC_LEVELS.map((level) => (
                        <option key={level} value={level}>
                          {level}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label htmlFor="grade_level" className="block text-sm font-medium text-gray-700">
                      Grade Level
                    </label>
                    <select
                      id="grade_level"
                      name="grade_level"
                      value={formData.grade_level}
                      onChange={handleChange}
                      className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    >
                      {GRADE_LEVELS.map((level) => (
                        <option key={level} value={level}>
                          {level}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label htmlFor="major" className="block text-sm font-medium text-gray-700">
                      Major/Field of Study (Optional)
                    </label>
                    <input
                      type="text"
                      name="major"
                      id="major"
                      value={formData.major}
                      onChange={handleChange}
                      className="mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Learning Preferences */}
            <div className="bg-white shadow px-4 py-5 sm:rounded-lg sm:p-6">
              <div className="md:grid md:grid-cols-3 md:gap-6">
                <div className="md:col-span-1">
                  <h3 className="text-lg font-medium leading-6 text-gray-900">
                    Learning Preferences
                  </h3>
                  <p className="mt-1 text-sm text-gray-500">
                    Help us understand how you learn best.
                  </p>
                </div>
                <div className="mt-5 md:mt-0 md:col-span-2 space-y-4">
                  <div>
                    <label htmlFor="subject_interest" className="block text-sm font-medium text-gray-700">
                      Subject Interests
                    </label>
                    <select
                      id="subject_interest"
                      name="subject_interest"
                      multiple
                      value={formData.subject_interest}
                      onChange={(e) => handleMultiSelect(e, 'subject_interest')}
                      className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    >
                      {SUBJECT_INTERESTS.map((subject) => (
                        <option key={subject} value={subject}>
                          {subject}
                        </option>
                      ))}
                    </select>
                    <p className="mt-1 text-sm text-gray-500">
                      Hold Ctrl/Cmd to select multiple subjects
                    </p>
                  </div>

                  <div>
                    <label htmlFor="learning_styles" className="block text-sm font-medium text-gray-700">
                      Learning Styles
                    </label>
                    <select
                      id="learning_styles"
                      name="learning_styles"
                      multiple
                      value={formData.learning_styles}
                      onChange={(e) => handleMultiSelect(e, 'learning_styles')}
                      className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    >
                      {LEARNING_STYLES.map((style) => (
                        <option key={style} value={style}>
                          {style}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label
                      htmlFor="preferred_study_methods"
                      className="block text-sm font-medium text-gray-700"
                    >
                      Preferred Study Methods
                    </label>
                    <select
                      id="preferred_study_methods"
                      name="preferred_study_methods"
                      multiple
                      value={formData.preferred_study_methods}
                      onChange={(e) => handleMultiSelect(e, 'preferred_study_methods')}
                      className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    >
                      {STUDY_METHODS.map((method) => (
                        <option key={method} value={method}>
                          {method}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label
                      htmlFor="preferred_difficulty"
                      className="block text-sm font-medium text-gray-700"
                    >
                      Preferred Difficulty
                    </label>
                    <select
                      id="preferred_difficulty"
                      name="preferred_difficulty"
                      value={formData.preferred_difficulty}
                      onChange={handleChange}
                      className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    >
                      {DIFFICULTY_LEVELS.map((level) => (
                        <option key={level} value={level}>
                          {level}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label
                      htmlFor="time_available_per_week"
                      className="block text-sm font-medium text-gray-700"
                    >
                      Time Available Per Week
                    </label>
                    <select
                      id="time_available_per_week"
                      name="time_available_per_week"
                      value={formData.time_available_per_week}
                      onChange={handleChange}
                      className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    >
                      {TIME_AVAILABILITY.map((time) => (
                        <option key={time} value={time}>
                          {time}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label
                      htmlFor="preferred_schedule"
                      className="block text-sm font-medium text-gray-700"
                    >
                      Preferred Schedule
                    </label>
                    <select
                      id="preferred_schedule"
                      name="preferred_schedule"
                      value={formData.preferred_schedule}
                      onChange={handleChange}
                      className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    >
                      {SCHEDULE_TYPES.map((type) => (
                        <option key={type} value={type}>
                          {type}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label
                      htmlFor="additional_notes"
                      className="block text-sm font-medium text-gray-700"
                    >
                      Additional Notes
                    </label>
                    <textarea
                      id="additional_notes"
                      name="additional_notes"
                      rows={3}
                      value={formData.additional_notes}
                      onChange={handleChange}
                      className="mt-1 focus:ring-indigo-500 focus:border-indigo-500 block w-full shadow-sm sm:text-sm border-gray-300 rounded-md"
                      placeholder="Any other information that might help personalize your learning experience..."
                    />
                  </div>
                </div>
              </div>
            </div>

            {error && (
              <div className="rounded-md bg-red-50 p-4">
                <div className="flex">
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-800">{error}</h3>
                  </div>
                </div>
              </div>
            )}

            {successMessage && (
              <div className="rounded-md bg-green-50 p-4">
                <div className="flex">
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-green-800">{successMessage}</h3>
                  </div>
                </div>
              </div>
            )}

            <div className="flex justify-end space-x-4">
              <button
                type="button"
                onClick={handleSkip}
                className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                Skip for Now
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
              >
                {isLoading ? 'Saving...' : 'Save Preferences'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </AppLayout>
  );
} 