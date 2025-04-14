'use client';

import { useState, useEffect, useRef } from 'react';
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

export default function SettingsPage() {
  const { user, isAuthenticated, isLoading, updatePreferences, checkAuth } = useAuth();
  const router = useRouter();
  const authChecked = useRef(false);
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
    if (!authChecked.current) {
      authChecked.current = true;
      checkAuth();
    }
  }, []);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/auth/login');
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (user?.preferences) {
      setFormData({
        name: user.preferences.name || '',
        level: user.preferences.level || 'Not Set',
        grade_level: user.preferences.grade_level || 'Not Set',
        major: user.preferences.major || '',
        subject_interest: user.preferences.subject_interest || [],
        learning_styles: user.preferences.learning_styles || [],
        preferred_study_methods: user.preferences.preferred_study_methods || [],
        preferred_difficulty: user.preferences.preferred_difficulty || 'Not Set',
        time_available_per_week: user.preferences.time_available_per_week || 'Not Set',
        preferred_schedule: user.preferences.preferred_schedule || 'Not Set',
        additional_notes: user.preferences.additional_notes || '',
        has_set_preferences: user.preferences.has_set_preferences || false,
        has_skipped_preferences: user.preferences.has_skipped_preferences || false,
      });
    }
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updatePreferences({
        ...formData,
        has_set_preferences: true,
        has_skipped_preferences: false,
      });
      router.push('/dashboard');
    } catch (error) {
      console.error('Failed to update preferences:', error);
    }
  };

  const handleSkip = async () => {
    try {
      await updatePreferences({
        ...formData,
        has_set_preferences: true,
        has_skipped_preferences: true,
      });
      router.push('/dashboard');
    } catch (error) {
      console.error('Failed to update preferences:', error);
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
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-t-4 border-b-4 border-blue-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <AppLayout>
      <div className="max-w-5xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="space-y-8">
          <div>
            <h1 className="text-4xl font-bold text-gray-900">Learning Preferences</h1>
            <p className="mt-2 text-lg text-gray-600">
              Customize your learning experience by setting your preferences below.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Personal Information */}
            <div className="bg-white shadow-lg rounded-2xl overflow-hidden">
              <div className="px-6 py-5 bg-gradient-to-r from-blue-600 to-blue-700">
                <h3 className="text-xl font-semibold text-white">Personal Information</h3>
                <p className="mt-1 text-blue-100">Tell us about yourself to help personalize your learning experience.</p>
              </div>
              <div className="px-6 py-6">
                <div className="grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-2">
                  <div>
                    <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                      Your Name
                    </label>
                    <input
                      type="text"
                      name="name"
                      id="name"
                      value={formData.name}
                      onChange={handleChange}
                      className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
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
                      className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
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
                      className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
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
                      Major/Field of Study
                    </label>
                    <input
                      type="text"
                      name="major"
                      id="major"
                      value={formData.major}
                      onChange={handleChange}
                      className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Learning Preferences */}
            <div className="bg-white shadow-lg rounded-2xl overflow-hidden">
              <div className="px-6 py-5 bg-gradient-to-r from-purple-600 to-purple-700">
                <h3 className="text-xl font-semibold text-white">Learning Preferences</h3>
                <p className="mt-1 text-purple-100">Help us understand how you prefer to learn.</p>
              </div>
              <div className="px-6 py-6 space-y-6">
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
                    className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900 min-h-[120px]"
                  >
                    {SUBJECT_INTERESTS.map((subject) => (
                      <option key={subject} value={subject}>
                        {subject}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-sm text-gray-500">Hold Ctrl/Cmd to select multiple</p>
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
                    className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900 min-h-[120px]"
                  >
                    {LEARNING_STYLES.map((style) => (
                      <option key={style} value={style}>
                        {style}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-sm text-gray-500">Hold Ctrl/Cmd to select multiple</p>
                </div>

                <div>
                  <label htmlFor="preferred_study_methods" className="block text-sm font-medium text-gray-700">
                    Preferred Study Methods
                  </label>
                  <select
                    id="preferred_study_methods"
                    name="preferred_study_methods"
                    multiple
                    value={formData.preferred_study_methods}
                    onChange={(e) => handleMultiSelect(e, 'preferred_study_methods')}
                    className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900 min-h-[120px]"
                  >
                    {STUDY_METHODS.map((method) => (
                      <option key={method} value={method}>
                        {method}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-sm text-gray-500">Hold Ctrl/Cmd to select multiple</p>
                </div>

                <div className="grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-2">
                  <div>
                    <label htmlFor="preferred_difficulty" className="block text-sm font-medium text-gray-700">
                      Preferred Difficulty
                    </label>
                    <select
                      id="preferred_difficulty"
                      name="preferred_difficulty"
                      value={formData.preferred_difficulty}
                      onChange={handleChange}
                      className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
                    >
                      {DIFFICULTY_LEVELS.map((level) => (
                        <option key={level} value={level}>
                          {level}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label htmlFor="time_available_per_week" className="block text-sm font-medium text-gray-700">
                      Time Available Per Week
                    </label>
                    <select
                      id="time_available_per_week"
                      name="time_available_per_week"
                      value={formData.time_available_per_week}
                      onChange={handleChange}
                      className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
                    >
                      {TIME_AVAILABILITY.map((time) => (
                        <option key={time} value={time}>
                          {time}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label htmlFor="preferred_schedule" className="block text-sm font-medium text-gray-700">
                      Preferred Schedule
                    </label>
                    <select
                      id="preferred_schedule"
                      name="preferred_schedule"
                      value={formData.preferred_schedule}
                      onChange={handleChange}
                      className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
                    >
                      {SCHEDULE_TYPES.map((type) => (
                        <option key={type} value={type}>
                          {type}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label htmlFor="additional_notes" className="block text-sm font-medium text-gray-700">
                    Additional Notes
                  </label>
                  <textarea
                    id="additional_notes"
                    name="additional_notes"
                    rows={4}
                    value={formData.additional_notes}
                    onChange={handleChange}
                    className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900"
                    placeholder="Any other information that might help personalize your learning experience..."
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end space-x-4 pt-6">
              <button
                type="button"
                onClick={handleSkip}
                className="px-6 py-3 border border-gray-300 shadow-sm text-sm font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
              >
                Skip for Now
              </button>
              <button
                type="submit"
                className="px-6 py-3 border border-transparent text-sm font-medium rounded-lg text-white bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all duration-200 shadow-md hover:shadow-lg"
              >
                Save Preferences
              </button>
            </div>
          </form>
        </div>
      </div>
    </AppLayout>
  );
} 