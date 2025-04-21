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
    mutationFn: async (message: string) => {
      console.log('[TIMEOUT-DEBUG] Starting message submission process', {
        time: new Date().toISOString(),
        sessionId: id,
        messageLength: message.length
      });
      
      try {
        // Step 1: Submit the message but don't wait for processing
        const submitResponse = await apiClient.chat.startMessageProcessing(id as string, message);
        const requestId = submitResponse.request_id;
        
        console.log('[TIMEOUT-DEBUG] Message submitted, received request ID:', requestId);
        
        // Step 2: Poll for results
        const startTime = performance.now();
        let elapsedTime = 0;
        let isComplete = false;
        let result = null;
        let lastPollTime = 0;
        let consecutiveEmptyResponses = 0;
        
        // Display initial loading message
        setChatHistory(prev => [
          ...prev.filter(msg => !(msg.role === 'assistant' && (msg.isTyping || msg.content === '...'))),
          { 
            role: 'assistant', 
            content: 'Generating response...', 
            timestamp: new Date().toISOString(),
            isTyping: true
          }
        ]);
        
        // Poll until complete or timeout
        while (!isComplete && elapsedTime < 7200000) { // 2 hour total limit (was 10 minutes)
          await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds between polls
          
          elapsedTime = performance.now() - startTime;
          lastPollTime = performance.now();
          
          try {
            // Update loading message periodically with time estimate
            if (elapsedTime > 30000) { // After 30 seconds, show time elapsed
              const timeElapsedSec = Math.round(elapsedTime / 1000);
              const timeElapsedMin = Math.floor(timeElapsedSec / 60);
              const remainingSec = timeElapsedSec % 60;
              const timeDisplay = timeElapsedMin > 0 
                ? `${timeElapsedMin}m ${remainingSec}s` 
                : `${timeElapsedSec}s`;
              
              setChatHistory(prev => {
                const filtered = prev.filter(msg => !(msg.role === 'assistant' && msg.isTyping));
                return [
                  ...filtered, 
                  { 
                    role: 'assistant', 
                    content: `Still working (${timeDisplay})... This process can take several minutes, please be patient.`, 
                    timestamp: new Date().toISOString(),
                    isTyping: true
                  }
                ];
              });
            }
            
            // Check if response is ready
            const statusResponse = await apiClient.chat.checkMessageStatus(id as string, requestId);
            
            if (statusResponse.status === 'complete') {
              if (statusResponse.result && statusResponse.result.content) {
                isComplete = true;
                result = statusResponse.result;
                console.log('[TIMEOUT-DEBUG] Response complete after', Math.round(elapsedTime / 1000), 'seconds');
                console.log('[TIMEOUT-DEBUG] Response content length:', result.content.length);
                console.log('[TIMEOUT-DEBUG] Response preview:', result.content.substring(0, 100));
                break;
              } else {
                console.warn('[TIMEOUT-DEBUG] Status is complete but result is empty or invalid');
                consecutiveEmptyResponses++;
                
                if (consecutiveEmptyResponses >= 3) {
                  // After 3 consecutive empty responses, try a different approach
                  console.warn('[TIMEOUT-DEBUG] Multiple empty responses detected, trying to fetch chat history');
                  const chatHistory = await apiClient.chat.getHistory(id as string);
                  
                  if (chatHistory && chatHistory.length > 0) {
                    // Find the latest assistant message
                    const latestAssistantMessage = [...chatHistory].reverse().find(msg => msg.role === 'assistant');
                    
                    if (latestAssistantMessage && latestAssistantMessage.content) {
                      console.log('[TIMEOUT-DEBUG] Found assistant message in history:', latestAssistantMessage);
                      isComplete = true;
                      result = latestAssistantMessage;
                      break;
                    }
                  }
                }
              }
            } else {
              console.log('[TIMEOUT-DEBUG] Still processing after', Math.round(elapsedTime / 1000), 'seconds');
              consecutiveEmptyResponses = 0; // Reset counter when we get a non-complete status
            }
          } catch (pollError) {
            console.error('[TIMEOUT-DEBUG] Error during polling:', pollError);
            
            // If polling error persists for over 30 seconds, try to fetch the latest messages directly
            if (performance.now() - lastPollTime > 30000) {
              try {
                console.warn('[TIMEOUT-DEBUG] Polling issues, trying direct chat history fetch');
                const chatHistory = await apiClient.chat.getHistory(id as string);
                
                if (chatHistory && chatHistory.length > 0) {
                  // Find the latest assistant message
                  const latestAssistantMessage = [...chatHistory].reverse().find(msg => msg.role === 'assistant');
                  
                  if (latestAssistantMessage && latestAssistantMessage.content) {
                    console.log('[TIMEOUT-DEBUG] Found assistant message in history:', latestAssistantMessage);
                    isComplete = true;
                    result = latestAssistantMessage;
                    break;
                  }
                }
              } catch (historyError) {
                console.error('[TIMEOUT-DEBUG] Failed to fetch chat history:', historyError);
              }
            }
            
            // Continue polling despite errors
          }
        }
        
        if (!isComplete) {
          throw new Error('Request processing exceeded maximum time limit (2 hours). The system may be overloaded or your request is too complex. Please try again later with a simpler query.');
        }
        
        return result;
      } catch (error) {
        console.error('[TIMEOUT-DEBUG] Error in message processing:', error);
        throw error;
      }
    },
    onMutate: () => {
      console.log('[TIMEOUT-DEBUG] onMutate triggered - adding user message', {
        time: new Date().toISOString()
      });
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
      
      // Check if this is likely a study plan request
      const isStudyPlanRequest = 
        chatMessage.toLowerCase().includes('study plan') || 
        chatMessage.toLowerCase().includes('plan for') || 
        chatMessage.toLowerCase().includes('create a plan');
      
      setTimeout(() => {
        setChatHistory(prev => [
          ...prev.filter(msg => !(msg.role === 'assistant' && (msg.isTyping || msg.content === '...'))), 
          { 
            role: 'assistant', 
            content: '...', 
            timestamp: new Date().toISOString(),
            isTyping: true,
            isStudyPlanRequest: isStudyPlanRequest // Add this flag to trigger the specialized UI
          }
        ]);
      }, 100);
    },
    onSuccess: (data: any) => {
      console.log('[TIMEOUT-DEBUG] onSuccess triggered - received response', {
        time: new Date().toISOString(),
        dataReceived: !!data,
        contentLength: data?.content?.length || 0
      });
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
      console.error('[TIMEOUT-DEBUG] onError triggered', {
        time: new Date().toISOString(),
        errorType: error.name,
        errorMessage: error.message,
        errorStack: error.stack
      });
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

  // Add a function to reset the chat UI if stuck
  const resetChat = () => {
    console.log('[DEBUG] Manually resetting chat UI state');
    setIsTyping(false);
    setChatError(null);
    
    // Reload chat history from server
    queryClient.invalidateQueries({ queryKey: ['chat', id] });
    
    // Remove any typing indicators
    setChatHistory(prev => 
      prev.filter(msg => !(msg.role === 'assistant' && (msg.isTyping || msg.content === '...')))
    );
    
    // Show a toast or notification
    alert('Chat interface has been reset. Please try sending a message again.');
  };

  // Add this component to your chat interface
  const ChatResetButton = () => (
    <button
      onClick={resetChat}
      className="px-3 py-2 bg-yellow-100 hover:bg-yellow-200 rounded-md flex items-center gap-1 text-sm text-yellow-800 absolute right-4 top-4"
    >
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
        <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
      </svg>
      Reset Chat
    </button>
  );

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
      
      // Check if this is a study plan request directly from the message flag
      // or by checking the previous message
      const hasStudyPlanFlag = message.isStudyPlanRequest === true;
      
      // Also check previous message as fallback approach
      const prevMessage = index > 0 ? chatHistory[index - 1] : null;
      const prevMessageIndicatesStudyPlan = prevMessage && 
        prevMessage.role === 'user' && 
        (prevMessage.content.toLowerCase().includes('study plan') || 
         prevMessage.content.toLowerCase().includes('plan for') ||
         prevMessage.content.includes('create a plan'));
      
      const isStudyPlanRequest = hasStudyPlanFlag || prevMessageIndicatesStudyPlan;
      
      if (isStudyPlanRequest) {
        // Enhanced typing indicator for study plan generation
        return (
          <div key={`typing-${index}`} className="text-left mb-4">
            <div className="inline-block p-4 rounded-lg bg-purple-50 text-gray-900 max-w-[80%] border border-purple-100">
              <div className="flex items-center mb-2">
                <div className="animate-spin h-5 w-5 mr-2 border-2 border-purple-600 border-t-transparent rounded-full"></div>
                <span className="font-medium text-purple-800">Generating Study Plan</span>
              </div>
              <p className="text-sm text-gray-600">
                Creating a personalized study plan with AI:
              </p>
              <ul className="text-xs mt-2 space-y-1 text-gray-500">
                <li>• Finding effective learning strategies...</li>
                <li>• Searching for recommended resources...</li>
                <li>• Creating a structured schedule...</li>
                <li className="text-xs italic mt-1">This may take 1-2 minutes</li>
              </ul>
            </div>
          </div>
        );
      }
      
      // Standard typing indicator with improved styling
      return (
        <div key={`typing-${index}`} className="text-left mb-4">
          <div className="inline-block p-3 rounded-lg bg-gray-100 text-gray-900 border border-gray-200 flex items-center space-x-2">
            <div className="flex space-x-1">
              <div className="animate-bounce h-2 w-2 bg-blue-500 rounded-full"></div>
              <div className="animate-bounce h-2 w-2 bg-blue-500 rounded-full" style={{ animationDelay: '0.2s' }}></div>
              <div className="animate-bounce h-2 w-2 bg-blue-500 rounded-full" style={{ animationDelay: '0.4s' }}></div>
            </div>
            <span className="text-xs text-gray-500">Generating response...</span>
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
    
    // Check if this message was generated by the multiagent system
    const isMultiagentResponse = message.role === 'assistant' && 
      (message.content.includes('STUDY PLAN OVERVIEW:') || 
       message.content.includes('DAY 1:') || 
       message.content.includes('DAY 2:') ||
       message.content.includes('WEEK 1-2:') ||
       message.content.includes('WEEK 3-4:') ||
       message.content.includes('SEARCH QUERIES USED:') ||
       message.content.includes('RESOURCES FOUND FOR THIS STRATEGY:'));
       
    // Check if this message contains an Ollama error
    const hasOllamaError = message.role === 'assistant' && 
      (message.content.includes('Cannot connect to Ollama server') || 
       message.content.includes('Error: Multiagent system not available') ||
       message.content.includes('To use the AI-powered study plan generator, please make sure Ollama is running') ||
       message.content.includes('I apologize, but I don\'t have access to language models at the moment'));
    
    console.log(`[DEBUG] Rendering message ${index}:`, {
      role: message.role,
      contentLength: message.content?.length || 0,
      contentPreview: message.content?.substring(0, 50),
      timestamp: message.timestamp,
      isMultiagentResponse,
      hasOllamaError
    });
    
    // Add a function to force refresh state and try again
    const handleRetryRequest = () => {
      console.log('[DEBUG] Forcing refresh of chat state');
      // Clear any error state
      setChatError(null);
      
      // Force invalidate the chat query to refresh from server
      queryClient.invalidateQueries({ queryKey: ['chat', id] });
      
      // Clear any typing indicators from the UI
      setChatHistory(prev => prev.filter(msg => !msg.isTyping));
      
      // Send a simple test message that will trigger a response
      sendMessageMutation.mutate('Hello, can you help me with my studies?');
    };
    
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
              : isMultiagentResponse 
                ? 'bg-purple-50 text-gray-900 border border-purple-100' 
                : hasOllamaError
                  ? 'bg-red-50 text-gray-900 border border-red-100'
                  : 'bg-gray-200 text-gray-900'
          }`}
        >
          {isMultiagentResponse && (
            <div className="mb-2 flex items-center">
              <span className="bg-purple-100 text-purple-800 text-xs font-medium me-2 px-2.5 py-0.5 rounded">
                AI Study Plan
              </span>
              <span className="text-xs text-gray-500">Generated with multi-agent planning</span>
            </div>
          )}
          
          {hasOllamaError && (
            <div className="mb-2 flex items-center">
              <span className="bg-red-100 text-red-800 text-xs font-medium me-2 px-2.5 py-0.5 rounded">
                Connection Error
              </span>
              <span className="text-xs text-gray-500">Ollama server not available</span>
            </div>
          )}
          
          <p className={`text-sm whitespace-pre-wrap break-words ${isMultiagentResponse ? 'font-serif leading-relaxed' : ''}`}>
            {message.content || '[Empty message]'}
          </p>
          
          {/* Add improved navigation links if this is a study plan */}
          {isMultiagentResponse && (
            <div className="mt-3 flex flex-wrap gap-2">
              <a href="#day-1" className="text-xs bg-purple-100 hover:bg-purple-200 text-purple-800 px-2 py-1 rounded-full">
                Day 1
              </a>
              <a href="#week-1" className="text-xs bg-purple-100 hover:bg-purple-200 text-purple-800 px-2 py-1 rounded-full">
                Week 1
              </a>
              <a href="#resources" className="text-xs bg-purple-100 hover:bg-purple-200 text-purple-800 px-2 py-1 rounded-full">
                Resources
              </a>
            </div>
          )}
          
          {message.timestamp && (
            <p className="text-xs mt-1 opacity-70">
              {new Date(message.timestamp).toLocaleTimeString()}
            </p>
          )}
          
          {hasOllamaError && (
            <div className="mt-3 p-2 bg-white rounded border border-red-100">
              <p className="text-xs font-medium text-red-700">How to fix:</p>
              <ol className="text-xs list-decimal list-inside text-gray-700 mt-1 space-y-1">
                <li>Open a terminal</li>
                <li>Run <code className="bg-gray-100 px-1 py-0.5 rounded">ollama run llama3:8b</code></li>
                <li>Keep the terminal window open while using the app</li>
                <li>Click the "Retry Connection" button below</li>
                <li>If the error persists, restart the backend server</li>
              </ol>
              
              <button 
                onClick={handleRetryRequest}
                className="mt-2 text-white bg-red-600 hover:bg-red-700 focus:ring-2 focus:outline-none focus:ring-red-300 font-medium rounded-lg text-xs px-3 py-1.5 text-center inline-flex items-center"
              >
                <svg className="w-3 h-3 me-1" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 18 18">
                  <path stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 1v6m0-6h6M3 17h6m6-6v6m0-6h-6"/>
                </svg>
                Retry Connection
              </button>
            </div>
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
                  <div className="bg-red-100 border border-red-200 text-red-700 px-4 py-2 rounded-md flex justify-between items-center">
                    <div>{chatError}</div>
                    <div className="flex gap-2">
                      <button 
                        className="text-red-700 hover:text-red-500 text-sm font-medium"
                        onClick={resetChat}
                      >
                        Reset Chat
                      </button>
                      <button 
                        className="text-red-700 hover:text-red-500"
                        onClick={() => setChatError(null)}
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                )}
                
                {/* Add reset button even when there's no error */}
                {!chatError && isTyping && (
                  <div className="flex justify-end">
                    <button
                      onClick={resetChat}
                      className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
                      </svg>
                      Reset UI if stuck
                    </button>
                  </div>
                )}
                
                <form onSubmit={handleChatSubmit} className="flex flex-col space-y-2">
                  <div className="flex space-x-2">
                    <textarea
                      value={chatMessage}
                      onChange={(e) => setChatMessage(e.target.value)}
                      onKeyDown={handleKeyPress}
                      placeholder="Type your message... Try asking 'Create a study plan for me' or 'Help me prepare for my exam'"
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
                  </div>
                  
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => setChatMessage("Create a personalized study plan for me with detailed daily activities")}
                      className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full transition-colors"
                    >
                      ✨ Create a study plan
                    </button>
                    <button
                      type="button"
                      onClick={() => setChatMessage(`Create a 2-week study plan for ${session.field_of_study} with specific resources and 2 hours per day`)}
                      className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full transition-colors"
                    >
                      📚 2-week study plan
                    </button>
                    <button
                      type="button"
                      onClick={() => setChatMessage(`I need a 30-day study plan for ${session.field_of_study} with daily activities and specific resources. I can study 3 hours per day and prefer visual learning.`)}
                      className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full transition-colors"
                    >
                      🔍 Detailed 30-day plan
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
} 