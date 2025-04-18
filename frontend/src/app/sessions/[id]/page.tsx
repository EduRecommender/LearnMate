'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import AppLayout from '@/components/layout/AppLayout';
import { StudySession } from '@/lib/sessions';
import { useAuth } from '@/lib/auth';

export default function SessionDetailPage() {
  const params = useParams();
  const id = params?.id as string;
  const router = useRouter();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'details' | 'resources' | 'chat'>('details');
  const [chatMessage, setChatMessage] = useState('');
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [isEditing, setIsEditing] = useState(false);
  const [editedSession, setEditedSession] = useState<Partial<StudySession> | null>(null);
  const [newResource, setNewResource] = useState({ name: '', url: '', type: 'URL' });
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Fetch session details
  const { data: session, isLoading, error } = useQuery<StudySession>({
    queryKey: ['session', id],
    queryFn: () => apiClient.sessions.get(id as string),
  });

  // Fetch chat history
  const { data: chatData, isLoading: isChatLoading } = useQuery({
    queryKey: ['chat', id],
    queryFn: () => apiClient.chat.getHistory(id as string),
    enabled: activeTab === 'chat',
    staleTime: 1000 * 60, // Cache for 1 minute
  });

  // Update session mutation
  const updateSessionMutation = useMutation({
    mutationFn: (data: Partial<StudySession>) => 
      apiClient.sessions.update(id as string, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session', id] });
      setIsEditing(false);
    },
  });

  // Send chat message mutation
  const sendMessageMutation = useMutation({
    mutationFn: (message: string) => 
      apiClient.chat.sendMessage(id as string, message),
    onMutate: () => {
      console.log('[DEBUG] onMutate triggered - setting typing indicator');
      // Optimistically add user message to the UI
      const newMessage = {
        role: 'user',
        content: chatMessage,
        timestamp: new Date().toISOString()
      };
      console.log('[DEBUG] Adding user message to chat UI:', newMessage);
      setChatHistory(prev => [...prev, newMessage]);
      setChatMessage('');
      setIsTyping(true);
      setChatError(null);
      
      // Explicitly add typing indicator message
      console.log('[DEBUG] Adding typing indicator to chat');
      setTimeout(() => {
        setChatHistory(prev => [
          ...prev, 
          { 
            role: 'assistant', 
            content: '...', 
            timestamp: new Date().toISOString(),
            isTyping: true
          }
        ]);
      }, 100);
    },
    onSuccess: (data) => {
      console.log('[DEBUG] onSuccess triggered - received response', data);
      // Add the assistant response
      console.log('[DEBUG] Response content type:', typeof data?.content);
      console.log('[DEBUG] Response content length:', data?.content?.length || 0);
      console.log('[DEBUG] Response content preview:', data?.content?.substring(0, 100));
      
      // Remove typing indicator and add real response
      console.log('[DEBUG] Removing typing indicator and adding real response');
      setChatHistory(prev => {
        console.log('[DEBUG] Current chat history:', prev);
        // Filter out typing indicators
        const filtered = prev.filter(msg => !(msg.role === 'assistant' && (msg.isTyping || msg.content === '...')));
        console.log('[DEBUG] Filtered chat history:', filtered);
        // Add the real response
        return [...filtered, {
          role: 'assistant',
          content: data.content,
          message_id: data.message_id,
          timestamp: data.timestamp
        }];
      });
      
      queryClient.invalidateQueries({ queryKey: ['chat', id] });
      setIsTyping(false);
    },
    onError: (error: any) => {
      console.error('[DEBUG] onError triggered:', error);
      setChatError(error.message || 'Failed to send message');
      setIsTyping(false);
      // Remove the typing indicator
      setChatHistory(prev => prev.filter(msg => !(msg.role === 'assistant' && (msg.isTyping || msg.content === '...'))));
    },
  });

  // Upload resource mutation
  const uploadResourceMutation = useMutation({
    mutationFn: (file: File) => 
      apiClient.sessions.uploadMaterial(id as string, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session', id] });
      setUploadError(null);
      setIsUploading(false);
    },
    onError: (error: any) => {
      setUploadError(error.message || 'Failed to upload file');
      setIsUploading(false);
    },
  });

  // Add URL resource mutation
  const addResourceMutation = useMutation({
    mutationFn: (resource: { name: string, url: string, type: string }) => 
      apiClient.sessions.uploadMaterial(id as string, new File([resource.url], resource.name)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session', id] });
      setNewResource({ name: '', url: '', type: 'URL' });
    },
  });

  // Upload syllabus mutation
  const uploadSyllabusMutation = useMutation({
    mutationFn: (file: File) => 
      apiClient.sessions.uploadSyllabus(id as string, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session', id] });
    },
  });

  // Initialize chat history when data is loaded
  useEffect(() => {
    if (chatData) {
      console.log('[DEBUG] Chat data received from API:', chatData);
      console.log('[DEBUG] Last message in chat history:', 
        chatData.length > 0 ? chatData[chatData.length - 1] : 'No messages');
      setChatHistory(chatData);
    }
  }, [chatData]);

  // Initialize edited session when session is loaded
  useEffect(() => {
    if (session) {
      setEditedSession(session);
    }
  }, [session]);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  if (isLoading) {
    return (
      <AppLayout>
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </AppLayout>
    );
  }

  if (error || !session) {
    return (
      <AppLayout>
        <div className="text-center py-12">
          <h2 className="text-2xl font-semibold text-gray-900">Error loading session</h2>
          <p className="mt-2 text-gray-600">Please try again later</p>
        </div>
      </AppLayout>
    );
  }

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editedSession) {
      updateSessionMutation.mutate(editedSession);
    }
  };

  const handleChatSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatMessage.trim()) return;
    
    // Add typing indicator
    sendMessageMutation.mutate(chatMessage);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleChatSubmit(e as any);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 100 * 1024 * 1024) { // 100MB limit
        setUploadError('File size exceeds 100MB limit');
        return;
      }
      setIsUploading(true);
      setUploadError(null);
      try {
        await uploadResourceMutation.mutateAsync(file);
      } catch (error) {
        console.error('Error uploading file:', error);
        setUploadError('Failed to upload file');
      }
    }
  };

  const handleAddResource = (e: React.FormEvent) => {
    e.preventDefault();
    if (newResource.name && newResource.url) {
      addResourceMutation.mutate(newResource);
    }
  };

  const handleSyllabusUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      try {
        await uploadSyllabusMutation.mutateAsync(file);
      } catch (error) {
        console.error('Error uploading syllabus:', error);
        setUploadError('Failed to upload syllabus');
      }
    }
  };

  const getSyllabusContent = () => {
    if (!session) return null;
    
    // Get processed resource ID if available
    const processedResourceId = session.syllabus?.processed_resource_id;
    const isProcessed = session.syllabus?.processed === true;
    
    // If session has syllabus data, display it nicely formatted
    if (isProcessed && (session.syllabus?.course_name || session.syllabus?.session_content)) {
      // Limit the number of topics shown
      const initialTopicsToShow = 10;
      const allTopics = session.syllabus.session_content || [];
      const displayedTopics = allTopics.slice(0, initialTopicsToShow);
      const hasMoreTopics = allTopics.length > initialTopicsToShow;
      
      return (
        <div className="mt-4 border border-gray-200 rounded-lg p-4 bg-white">
          {session.syllabus.course_name && (
            <h3 className="text-lg font-semibold text-gray-900 mb-3">{session.syllabus.course_name}</h3>
          )}
          {allTopics.length > 0 && (
            <div>
              <h4 className="text-md font-medium text-gray-700 mb-2">Session Content:</h4>
              <ul className="pl-5 space-y-1 list-disc max-h-60 overflow-y-auto">
                {displayedTopics.map((topic: string, index: number) => (
                  <li key={index} className="text-sm text-gray-900">
                    {topic}
                  </li>
                ))}
                {hasMoreTopics && (
                  <li className="text-sm text-gray-500 italic">
                    ... and {allTopics.length - initialTopicsToShow} more topics
                  </li>
                )}
              </ul>
              
              {processedResourceId && (
                <div className="mt-4 text-sm">
                  <a 
                    href={`/api/v1/sessions/${session.id}/resources/${processedResourceId}/download`}
                    className="text-blue-600 hover:text-blue-800 font-medium flex items-center"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    View complete syllabus
                  </a>
                </div>
              )}
            </div>
          )}
        </div>
      );
    }
    
    // If the syllabus processing failed or wasn't processed
    if (session.syllabus?.error) {
      return (
        <div className="mt-4 border border-red-100 rounded-lg p-4 bg-red-50 text-red-800">
          <p className="font-medium">Processing error:</p>
          <p className="text-sm">{session.syllabus.error}</p>
        </div>
      );
    }
    
    // Default case
    return null;
  };

  const getResourcePreview = (resource: any) => {
    // Helper function to get file URL
    const getFileUrl = (resource: any) => {
      if (!resource || !resource.id) return "";
      return `/api/v1/sessions/${session.id}/resources/${resource.id}/download`;
    };
    
    // Check if this is a processed syllabus text resource
    if (resource.metadata?.is_syllabus && resource.metadata?.is_processed && resource.type === 'text' && resource.content) {
      // Get just the first few lines for a compact preview
      const lines = resource.content.split('\n');
      const courseNameLine = lines.find((line: string) => line.startsWith('#')) || 'Syllabus Content';
      const previewLines = lines.filter((line: string) => line.trim() && line.startsWith('-')).slice(0, 3);
      
      return (
        <div className="mt-2 p-3 border rounded bg-gray-50 text-sm text-gray-800">
          <p className="font-medium">{courseNameLine.replace('#', '').trim()}</p>
          {previewLines.length > 0 && (
            <ul className="mt-1 pl-4 list-disc text-xs text-gray-600">
              {previewLines.map((line: string, i: number) => (
                <li key={i}>{line.replace('-', '').trim()}</li>
              ))}
            </ul>
          )}
          {lines.length > 4 && (
            <p className="text-xs text-gray-500 mt-1 italic">... and more</p>
          )}
          <div className="mt-2 text-right">
            <a 
              href={getFileUrl(resource)}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-600 hover:text-blue-800 font-medium"
            >
              View full content
            </a>
          </div>
        </div>
      );
    }
    
    // The rest of your existing preview logic for other resource types
    const fileUrl = getFileUrl(resource);
    
    if (!fileUrl) return null;
    
    // Image preview
    if (resource.metadata?.content_type?.startsWith('image/')) {
      return (
        <div className="mt-2">
          <img 
            src={fileUrl} 
            alt={resource.name} 
            className="max-h-40 object-contain rounded border"
          />
        </div>
      );
    }
    
    // PDF preview
    if (resource.metadata?.content_type === 'application/pdf') {
      return (
        <div className="mt-2">
          <embed 
            src={`${fileUrl}#toolbar=0&navpanes=0&scrollbar=0`} 
            type="application/pdf"
            className="w-full h-40 rounded border"
          />
        </div>
      );
    }
    
    return null;
  };

  // Render chat messages with debug info
  const renderChatMessage = (message: any, index: number) => {
    // Safety check for undefined or null messages
    if (!message) {
      console.error('[DEBUG] Found null/undefined message at index', index);
      return null;
    }
    
    // Check if this is a typing indicator
    if (message.isTyping || (message.role === 'assistant' && message.content === '...')) {
      console.log('[DEBUG] Rendering typing indicator at index', index);
      return (
        <div key={`typing-${index}`} className="text-left mb-4">
          <div className="inline-block p-3 rounded-lg bg-gray-200 text-gray-900">
            <div className="flex space-x-1">
              <div className="animate-bounce h-2 w-2 bg-gray-500 rounded-full"></div>
              <div className="animate-bounce h-2 w-2 bg-gray-500 rounded-full" style={{ animationDelay: '0.2s' }}></div>
              <div className="animate-bounce h-2 w-2 bg-gray-500 rounded-full" style={{ animationDelay: '0.4s' }}></div>
            </div>
          </div>
        </div>
      );
    }
    
    // Safety check for message content
    if (!message.content) {
      console.error('[DEBUG] Message has no content:', message);
      // Try to extract content from possible nested structure
      if (message.data && message.data.content) {
        console.log('[DEBUG] Found content in message.data:', message.data.content);
        message.content = message.data.content;
      } else {
        message.content = "[Message content unavailable]";
      }
    }
    
    console.log(`[DEBUG] Rendering message ${index}:`, {
      role: message.role,
      contentLength: message.content?.length || 0,
      contentPreview: message.content?.substring(0, 50),
      timestamp: message.timestamp
    });
    
    return (
      <div
        key={message.message_id || index}
        className={`mb-4 ${
          message.role === 'user' ? 'text-right' : 'text-left'
        }`}
      >
        <div
          className={`inline-block p-3 rounded-lg max-w-[80%] ${
            message.role === 'user'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-900'
          }`}
        >
          <p className="text-sm whitespace-pre-wrap break-words">
            {message.content || '[Empty message]'}
          </p>
          {message.timestamp && (
            <p className="text-xs mt-1 opacity-70">
              {new Date(message.timestamp).toLocaleTimeString()}
            </p>
          )}
        </div>
      </div>
    );
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-semibold text-gray-900">
            {isEditing ? (
              <input
                type="text"
                value={editedSession?.name || ''}
                onChange={(e) => setEditedSession(prev => ({ ...prev, name: e.target.value }))}
                className="border rounded px-2 py-1"
              />
            ) : (
              session.name
            )}
          </h1>
          <div className="flex space-x-2">
            {isEditing ? (
              <>
                <button
                  onClick={handleEditSubmit}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                >
                  Save
                </button>
                <button
                  onClick={() => setIsEditing(false)}
                  className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
                >
                  Cancel
                </button>
              </>
            ) : (
              <button
                onClick={() => setIsEditing(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Edit
              </button>
            )}
          </div>
        </div>

        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px">
              <button
                onClick={() => setActiveTab('details')}
                className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
                  activeTab === 'details'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Details
              </button>
              <button
                onClick={() => setActiveTab('resources')}
                className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
                  activeTab === 'resources'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Resources
              </button>
              <button
                onClick={() => setActiveTab('chat')}
                className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
                  activeTab === 'chat'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Chat
              </button>
            </nav>
          </div>

          <div className="p-6">
            {activeTab === 'details' && (
              <div className="space-y-4">
                {isEditing ? (
                  <form onSubmit={handleEditSubmit} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Field of Study</label>
                      <input
                        type="text"
                        value={editedSession?.field_of_study || ''}
                        onChange={(e) => setEditedSession(prev => ({ ...prev, field_of_study: e.target.value }))}
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Study Goal</label>
                      <textarea
                        value={editedSession?.study_goal || ''}
                        onChange={(e) => setEditedSession(prev => ({ ...prev, study_goal: e.target.value }))}
                        rows={3}
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Time Commitment (hours)</label>
                      <input
                        type="number"
                        value={editedSession?.time_commitment || 0}
                        onChange={(e) => setEditedSession(prev => ({ ...prev, time_commitment: parseFloat(e.target.value) }))}
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Difficulty Level</label>
                      <select
                        value={editedSession?.difficulty_level || 'beginner'}
                        onChange={(e) => setEditedSession(prev => ({ ...prev, difficulty_level: e.target.value }))}
                        className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      >
                        <option value="beginner">Beginner</option>
                        <option value="intermediate">Intermediate</option>
                        <option value="advanced">Advanced</option>
                      </select>
                    </div>
                  </form>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Field of Study</h3>
                      <p className="mt-1 text-sm text-gray-900">{session.field_of_study}</p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Study Goal</h3>
                      <p className="mt-1 text-sm text-gray-900">{session.study_goal}</p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Time Commitment</h3>
                      <p className="mt-1 text-sm text-gray-900">{session.time_commitment} hours</p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Difficulty Level</h3>
                      <p className="mt-1 text-sm text-gray-900">{session.difficulty_level}</p>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-500">Progress</h3>
                      <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${typeof session.progress === 'number' ? session.progress : 0}%` }}
                        ></div>
                      </div>
                      <p className="mt-1 text-sm text-gray-900">{typeof session.progress === 'number' ? session.progress : 0}%</p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'resources' && (
              <div className="space-y-6">
                {/* Display processed syllabus content if available */}
                {getSyllabusContent()}
                
                <div className="bg-gray-50 p-4 rounded-md">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Upload Syllabus</h3>
                  <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md">
                    <div className="space-y-1 text-center">
                      <svg
                        className="mx-auto h-12 w-12 text-gray-400"
                        stroke="currentColor"
                        fill="none"
                        viewBox="0 0 48 48"
                        aria-hidden="true"
                      >
                        <path
                          d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                          strokeWidth={2}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                      <div className="flex text-sm text-gray-600">
                        <label
                          htmlFor="syllabus-upload"
                          className="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-blue-500"
                        >
                          <span>Upload syllabus</span>
                          <input
                            id="syllabus-upload"
                            name="syllabus-upload"
                            type="file"
                            className="sr-only"
                            onChange={handleSyllabusUpload}
                            accept=".pdf,.doc,.docx"
                          />
                        </label>
                        <p className="pl-1">or drag and drop</p>
                      </div>
                      <p className="text-xs text-gray-500">PDF, DOC, DOCX up to 10MB</p>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 p-4 rounded-md">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Add Resource</h3>
                  <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md">
                    <div className="space-y-1 text-center">
                      <svg
                        className="mx-auto h-12 w-12 text-gray-400"
                        stroke="currentColor"
                        fill="none"
                        viewBox="0 0 48 48"
                        aria-hidden="true"
                      >
                        <path
                          d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                          strokeWidth={2}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                      <div className="flex text-sm text-gray-600">
                        <label
                          htmlFor="resource-upload"
                          className="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-blue-500"
                        >
                          <span>Upload file</span>
                          <input
                            id="resource-upload"
                            name="resource-upload"
                            type="file"
                            className="sr-only"
                            onChange={handleFileUpload}
                            accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png"
                          />
                        </label>
                        <p className="pl-1">or drag and drop</p>
                      </div>
                      <p className="text-xs text-gray-500">PDF, DOC, DOCX, TXT, JPG, PNG up to 100MB</p>
                      {isUploading && (
                        <div className="mt-2">
                          <div className="animate-pulse flex space-x-4">
                            <div className="flex-1 space-y-4 py-1">
                              <div className="h-2 bg-blue-200 rounded w-3/4"></div>
                            </div>
                          </div>
                        </div>
                      )}
                      {uploadError && (
                        <div className="mt-2 text-sm text-red-600">
                          {uploadError}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="mt-6 border-t border-gray-200 pt-4">
                    <h4 className="text-sm font-medium text-gray-900 mb-2">Or add a URL resource</h4>
                    <form onSubmit={handleAddResource} className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700">Resource Name</label>
                        <input
                          type="text"
                          value={newResource.name}
                          onChange={(e) => setNewResource(prev => ({ ...prev, name: e.target.value }))}
                          className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                          placeholder="Enter resource name"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700">URL</label>
                        <input
                          type="url"
                          value={newResource.url}
                          onChange={(e) => setNewResource(prev => ({ ...prev, url: e.target.value }))}
                          className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                          placeholder="https://example.com"
                        />
                      </div>
                      <button
                        type="submit"
                        className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                      >
                        Add URL Resource
                      </button>
                    </form>
                  </div>
                </div>

                <div className="mt-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Resources</h3>
                  {session.resources && session.resources.length > 0 ? (
                    <ul className="divide-y divide-gray-200">
                      {session.resources.map((resource: any) => (
                        <li key={resource.id} className="py-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm font-medium text-gray-900">{resource.name}</p>
                              <p className="text-sm text-gray-500">
                                {resource.metadata?.content_type || resource.type}
                                {resource.metadata?.size && ` • ${(resource.metadata.size / 1024).toFixed(1)} KB`}
                                {resource.metadata?.uploaded_at && ` • ${new Date(resource.metadata.uploaded_at).toLocaleDateString()}`}
                              </p>
                            </div>
                            <div className="flex space-x-2">
                              <a
                                href={`/api/v1/sessions/${session.id}/resources/${resource.id}/download`}
                                download={resource.name}
                                className="text-sm text-blue-600 hover:text-blue-500"
                              >
                                Download
                              </a>
                              <button
                                onClick={() => {
                                  if (confirm('Are you sure you want to delete this resource?')) {
                                    apiClient.sessions.deleteMaterial(session.id.toString(), resource.id.toString());
                                    queryClient.invalidateQueries({ queryKey: ['session', id] });
                                  }
                                }}
                                className="text-sm text-red-600 hover:text-red-500"
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                          {getResourcePreview(resource)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-gray-500">No resources added yet.</p>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'chat' && (
              <div className="space-y-4">
                <div className="h-96 overflow-y-auto border rounded-md p-4 bg-gray-50">
                  {isChatLoading ? (
                    <div className="flex justify-center items-center h-full">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                    </div>
                  ) : chatHistory.length > 0 ? (
                    <div className="space-y-4">
                      {chatHistory.map((message, index) => renderChatMessage(message, index))}
                      <div ref={chatEndRef} />
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500">
                      <p>No messages yet. Start a conversation!</p>
                    </div>
                  )}
                </div>
                
                {chatError && (
                  <div className="bg-red-100 border border-red-200 text-red-700 px-4 py-2 rounded-md">
                    {chatError}
                    <button 
                      className="ml-2 text-red-700 hover:text-red-500"
                      onClick={() => setChatError(null)}
                    >
                      Dismiss
                    </button>
                  </div>
                )}
                
                <form onSubmit={handleChatSubmit} className="flex space-x-2">
                  <textarea
                    value={chatMessage}
                    onChange={(e) => setChatMessage(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
                    className="flex-1 border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm min-h-[60px] resize-y"
                    disabled={sendMessageMutation.isPending}
                  />
                  <button
                    type="submit"
                    disabled={sendMessageMutation.isPending || !chatMessage.trim()}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {sendMessageMutation.isPending ? (
                      <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                    ) : (
                      'Send'
                    )}
                  </button>
                </form>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
} 