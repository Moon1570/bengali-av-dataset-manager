import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getNextVideo, getShortVideos, claimVideo, startProcessing, submitResults, submitReview } from '../api';

// Workflow stages
const STAGES = {
  LOADING: 'loading',
  PREVIEW: 'preview',
  PROCESSING: 'processing',
  CHUNK_REVIEW: 'chunk_review',
  REVIEWING: 'reviewing',
  COMPLETE: 'complete',
  ERROR: 'error',
  NO_VIDEOS: 'no_videos',
  SHORT_VIDEO_PICKER: 'short_video_picker'
};

function VideoQueue({ user }) {
  const [stage, setStage] = useState(STAGES.LOADING);
  const [video, setVideo] = useState(null);
  const [videoQueue, setVideoQueue] = useState([]); // Local queue of videos
  const [shortVideos, setShortVideos] = useState([]); // Short videos for picker
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState('balanced');
  const [selectedTranscriptionModel, setSelectedTranscriptionModel] = useState('google');
  const [selectedVideoDomain, setSelectedVideoDomain] = useState(''); // Video domain
  const [jobId, setJobId] = useState(null);
  const [error, setError] = useState('');
  
  // Processing state
  const [processingLogs, setProcessingLogs] = useState([]);
  const [processingProgress, setProcessingProgress] = useState(0);
  
  // Processing history check
  const [processingHistory, setProcessingHistory] = useState(null);
  const [checkingHistory, setCheckingHistory] = useState(false);
  
  // Results state
  const [results, setResults] = useState(null);
  const [processedChunks, setProcessedChunks] = useState([]);
  const [chunksToDelete, setChunksToDelete] = useState(new Set());
  const [selectedFormat, setSelectedFormat] = useState({}); // Track selected format per chunk
  
  // Review state
  const [reviewData, setReviewData] = useState({
    audio_quality: 3,
    video_quality: 3,
    transcription_quality: 3,
    overall_quality: 3,
    has_issues: false,
    issue_notes: '',
    wrong_language: false,
    poor_audio: false,
    no_face: false,
    bad_sync: false,
    wrong_content: false
  });

  useEffect(() => {
    loadNextVideo();
  }, []);

  const loadNextVideo = async () => {
    try {
      setStage(STAGES.LOADING);
      setProcessingHistory(null); // Reset history
      setChunksToDelete(new Set()); // Reset deletion state
      setSelectedFormat({}); // Reset format selection
      
      // If we have videos in the queue, use the next one
      if (videoQueue.length > 0) {
        const nextVideo = videoQueue[0];
        setVideo(nextVideo);
        setVideoQueue(prev => prev.slice(1)); // Remove first video from queue
        setSelectedPreset('balanced');
        setSelectedTranscriptionModel('google');
        // Set video domain: use video_domain if available, otherwise fallback to speaker_domain
        setSelectedVideoDomain(nextVideo.video_domain || nextVideo.speaker_domain || 'general');
        checkVideoProcessingHistory(nextVideo.video_id);
        setStage(STAGES.PREVIEW);
        
        // If queue is running low (< 2 videos), fetch more in background
        if (videoQueue.length < 2) {
          fetchMoreVideos();
        }
        return;
      }
      
      // No videos in queue, fetch from server
      const response = await getNextVideo();
      
      if (response.data.videos && response.data.videos.length > 0) {
        const firstVideo = response.data.videos[0];
        setVideo(firstVideo);
        setVideoQueue(response.data.videos.slice(1)); // Store remaining videos
        setPresets(response.data.presets);
        setSelectedPreset('balanced');
        setSelectedTranscriptionModel('google');
        // Set video domain: use video_domain if available, otherwise fallback to speaker_domain
        setSelectedVideoDomain(firstVideo.video_domain || firstVideo.speaker_domain || 'general');
        checkVideoProcessingHistory(firstVideo.video_id);
        setStage(STAGES.PREVIEW);
      } else {
        setStage(STAGES.NO_VIDEOS);
      }
    } catch (error) {
      if (error.response?.status === 404) {
        setStage(STAGES.NO_VIDEOS);
      } else {
        setError(error.response?.data?.error || 'Failed to load video');
        setStage(STAGES.ERROR);
      }
    }
  };

  const fetchMoreVideos = async () => {
    try {
      const response = await getNextVideo();
      if (response.data.videos && response.data.videos.length > 0) {
        setVideoQueue(prev => [...prev, ...response.data.videos]);
      }
    } catch (error) {
      console.error('Failed to fetch more videos:', error);
      // Don't show error to user, just log it
    }
  };

  const handleSkipVideo = async () => {
    try {
      setStage(STAGES.LOADING);
      
      // Just load the next video from queue (no need to call skip API)
      await loadNextVideo();
    } catch (error) {
      console.error('Failed to skip video:', error);
      // Even if skip fails, try to load next video
      loadNextVideo();
    }
  };

  const handleSearchShortVideos = async () => {
    try {
      setStage(STAGES.LOADING);
      const response = await getShortVideos(120); // Get videos under 2 minutes
      
      if (response.data.videos && response.data.videos.length > 0) {
        setShortVideos(response.data.videos);
        setStage(STAGES.SHORT_VIDEO_PICKER);
      } else {
        setError('No short videos available');
        setStage(STAGES.ERROR);
      }
    } catch (error) {
      setError(error.response?.data?.message || 'Failed to load short videos');
      setStage(STAGES.ERROR);
    }
  };

  const handleSelectShortVideo = (selectedVideo) => {
    setVideo(selectedVideo);
    setShortVideos([]);
    setSelectedPreset('balanced');
    setSelectedTranscriptionModel('google');
    checkVideoProcessingHistory(selectedVideo.video_id);
    setStage(STAGES.PREVIEW);
  };

  const checkVideoProcessingHistory = async (videoId) => {
    setCheckingHistory(true);
    try {
      const response = await fetch(`http://localhost:5000/api/videos/${videoId}/check-processed`, {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        setProcessingHistory(data);
      }
    } catch (error) {
      console.error('Failed to check processing history:', error);
      setProcessingHistory(null);
    } finally {
      setCheckingHistory(false);
    }
  };

  const handleClaimVideo = async () => {
  try {
    setStage(STAGES.LOADING);
    const response = await claimVideo(video.video_id, selectedPreset);
    setJobId(response.data.job_id);
    
    // Mark as processing in backend
    await startProcessing(video.video_id);
    
    setStage(STAGES.PROCESSING);
    setProcessingLogs(['🚀 Initializing processing...']);
    setProcessingProgress(0);
    
    // Start real processing
    await startRealProcessing();
    
  } catch (error) {
    setError(error.response?.data?.error || 'Failed to claim video');
    setStage(STAGES.ERROR);
  }
};

const startRealProcessing = async () => {
  try {
    console.log('🚀 Starting real processing for:', video.video_id);
    
    const response = await fetch(`http://localhost:5000/api/videos/${video.video_id}/process-real`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        transcription_model: selectedTranscriptionModel,
        preset: selectedPreset,
        youtube_url: video.youtube_url 
      })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to start processing');
    }
    
    const data = await response.json();
    console.log('✅ Processing started:', data);
    
    setProcessingLogs(prev => [...prev, '✅ Processing started on server']);
    
    // Start polling for status
    pollProcessingStatus();
    
  } catch (error) {
    console.error('❌ Failed to start processing:', error);
    setError('Failed to start processing: ' + error.message);
    setStage(STAGES.ERROR);
  }
};

const pollProcessingStatus = () => {
  let pollCount = 0;
  const maxPolls = 2160; // 3 hours (2160 * 5 seconds)
  
  const pollInterval = setInterval(async () => {
    try {
      pollCount++;
      console.log(`📊 Polling status for video: ${video.video_id} (${pollCount}/${maxPolls})`);
      
      const response = await fetch(
        `http://localhost:5000/api/videos/${video.video_id}/processing-status`,
        { credentials: 'include' }
      );
      
      console.log('📡 Status response:', response.status);
      
      if (!response.ok) {
        throw new Error('Failed to get status');
      }
      
      const data = await response.json();
      console.log('📊 Status data:', data);
      
      // Update logs and calculate progress from steps
      if (data.logs && data.logs.length > 0) {
        setProcessingLogs(data.logs);
        
        // Parse logs to determine progress based on steps
        const allLogs = data.logs.join('\n');
        
        let calculatedProgress = 5; // Start at 5%
        
        // Detect steps from logs
        if (allLogs.includes('Step 1/4') || allLogs.includes('Downloading video')) {
          calculatedProgress = Math.max(calculatedProgress, 10);
        }
        if (allLogs.includes('Downloaded:') || allLogs.includes('Step 2/4')) {
          calculatedProgress = Math.max(calculatedProgress, 25);
        }
        if (allLogs.includes('Processing with Docker') || allLogs.includes('Running command')) {
          calculatedProgress = Math.max(calculatedProgress, 30);
        }
        if (allLogs.includes('Docker container') || allLogs.includes('Starting pipeline')) {
          calculatedProgress = Math.max(calculatedProgress, 35);
        }
        if (allLogs.includes('Extracting audio') || allLogs.includes('Audio extraction')) {
          calculatedProgress = Math.max(calculatedProgress, 45);
        }
        if (allLogs.includes('Face detection') || allLogs.includes('Processing faces')) {
          calculatedProgress = Math.max(calculatedProgress, 55);
        }
        if (allLogs.includes('Transcription') || allLogs.includes('Transcribing')) {
          calculatedProgress = Math.max(calculatedProgress, 65);
        }
        if (allLogs.includes('Synchronization') || allLogs.includes('Calculating sync')) {
          calculatedProgress = Math.max(calculatedProgress, 75);
        }
        if (allLogs.includes('Step 3/4') || allLogs.includes('Collecting results')) {
          calculatedProgress = Math.max(calculatedProgress, 85);
        }
        if (allLogs.includes('Step 4/4') || allLogs.includes('Updating database')) {
          calculatedProgress = Math.max(calculatedProgress, 95);
        }
        
        setProcessingProgress(calculatedProgress);
      }
      
      // Override with explicit progress if provided
      if (data.progress !== undefined && data.progress !== null) {
        console.log('📈 Progress updated:', data.progress);
        setProcessingProgress(data.progress);
      }
      
      if (data.status === 'completed') {
        clearInterval(pollInterval);
        console.log('✅ Processing complete! Results:', data.results);
        
        setProcessingProgress(100);
        setProcessingLogs(prev => [...prev, '✅ Processing complete!']);
        
        // Set results
        setResults(data.results);
        
        // Fetch chunk information for review
        console.log(`📦 Fetching chunks for video: ${video.video_id}`);
        try {
          const chunksResponse = await fetch(
            `http://localhost:5000/api/videos/${video.video_id}/chunks`,
            { credentials: 'include' }
          );
          
          console.log(`📦 Chunks response status: ${chunksResponse.status}`);
          
          if (chunksResponse.ok) {
            const chunksData = await chunksResponse.json();
            console.log(`📦 Fetched ${chunksData.chunks?.length || 0} chunks:`, chunksData);
            setProcessedChunks(chunksData.chunks || []);
            
            if (chunksData.chunks && chunksData.chunks.length > 0) {
              console.log('✅ Chunks loaded successfully');
            } else {
              console.warn('⚠️ No chunks found in response');
            }
          } else {
            const errorData = await chunksResponse.json();
            console.error('❌ Failed to fetch chunks:', errorData);
          }
        } catch (error) {
          console.error('❌ Error fetching chunks:', error);
        }
        
        setTimeout(() => {
          setStage(STAGES.CHUNK_REVIEW);
        }, 1000);
        
      } else if (data.status === 'failed') {
        clearInterval(pollInterval);
        console.error('❌ Processing failed:', data.error);
        setError('Processing failed: ' + data.error);
        setStage(STAGES.ERROR);
        
      } else if (data.status === 'not_found') {
        console.warn('⚠️ Status not found, might not have started yet');
        // Keep polling
      }
      
      // Timeout check
      if (pollCount >= maxPolls) {
        clearInterval(pollInterval);
        setError('Processing timeout - took longer than 3 hours');
        setStage(STAGES.ERROR);
      }
      
    } catch (error) {
      console.error('❌ Polling error:', error);
      // Don't stop polling on network errors, might be temporary
    }
  }, 5000); // Poll every 5 seconds
};

  const runRealProcessing = async () => {
    try {
      console.log('🎬 Starting real processing for video:', video.video_id);
      setProcessingLogs(['🎬 Starting real processing...']);
      setProcessingProgress(5);
      
      // Call backend to trigger worker script
      const response = await fetch(`http://localhost:5000/api/videos/${video.video_id}/process-local`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          preset: selectedPreset,
          youtube_url: video.youtube_url 
        })
      });
      
      console.log('📡 Process-local response status:', response.status);
      
      if (!response.ok) {
        const errorData = await response.json();
        console.error('❌ Processing failed:', errorData);
        throw new Error(errorData.error || 'Processing failed');
      }
      
      const data = await response.json();
      console.log('✅ Processing started:', data);
      
      // Poll for results
      pollProcessingStatus(video.video_id);
      
    } catch (error) {
      console.error('❌ runRealProcessing error:', error);
      setError('Processing failed: ' + error.message);
      setStage(STAGES.ERROR);
    }
  };



  const handleSubmitResults = async () => {
    try {
      await submitResults(video.video_id, results);
      // Results submitted, now in review stage (already set)
    } catch (error) {
      setError('Failed to submit results');
    }
  };

  const handleReview = async (decision) => {
    try {
      const reviewPayload = {
        ...reviewData,
        decision,
        issue_categories: getIssueCategories()
      };
      
      await submitReview(video.video_id, reviewPayload);
      setStage(STAGES.COMPLETE);
      
      // Auto-load next video after 2 seconds
      setTimeout(() => {
        loadNextVideo();
      }, 2000);
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to submit review');
    }
  };

  const getIssueCategories = () => {
    const categories = [];
    if (reviewData.wrong_language) categories.push('wrong_language');
    if (reviewData.poor_audio) categories.push('poor_audio');
    if (reviewData.no_face) categories.push('no_face');
    if (reviewData.bad_sync) categories.push('bad_sync');
    if (reviewData.wrong_content) categories.push('wrong_content');
    return categories;
  };

  const updateReviewField = (field, value) => {
    setReviewData(prev => ({ ...prev, [field]: value }));
  };

  const getDomainBadgeColor = (domain) => {
    const colors = {
      'food_blogger': 'bg-yellow-100 text-yellow-800',
      'academician': 'bg-blue-100 text-blue-800',
      'economic': 'bg-green-100 text-green-800',
      'financial': 'bg-purple-100 text-purple-800',
      'motivational_speaker': 'bg-pink-100 text-pink-800',
      'comedian': 'bg-orange-100 text-orange-800',
      'sports_and_gaming': 'bg-red-100 text-red-800',
      'general': 'bg-gray-100 text-gray-800'
    };
    return colors[domain] || colors['general'];
  };

  const updateVideoDomain = async (newDomain) => {
    try {
      const response = await fetch(`http://localhost:5000/api/videos/${video.video_id}/update-domain`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain: newDomain })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to update domain');
      }

      setSelectedVideoDomain(newDomain);
      // Update video object
      setVideo(prev => ({ ...prev, video_domain: newDomain }));
    } catch (error) {
      console.error('Failed to update domain:', error);
      setError('Failed to update domain: ' + error.message);
    }
  };

  // Render based on stage
  if (stage === STAGES.LOADING) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-xl text-gray-600">Loading...</div>
        </div>
      </div>
    );
  }

  if (stage === STAGES.NO_VIDEOS) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-2xl mx-auto">
          <div className="bg-white rounded-xl shadow-md p-8 text-center">
            <div className="text-6xl mb-4">🎉</div>
            <h2 className="text-2xl font-bold text-gray-800 mb-2">No Videos Available</h2>
            <p className="text-gray-600 mb-6">
              All videos in the queue have been processed! Check back later or contact admin.
            </p>
            <Link
              to="/"
              className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded-lg"
            >
              Back to Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (stage === STAGES.ERROR) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-2xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-xl p-8 text-center">
            <div className="text-6xl mb-4">⚠️</div>
            <h2 className="text-2xl font-bold text-red-800 mb-2">Error</h2>
            <p className="text-red-600 mb-6">{error}</p>
            <button
              onClick={() => loadNextVideo()}
              className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded-lg"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (stage === STAGES.COMPLETE) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-2xl mx-auto">
          <div className="bg-green-50 border border-green-200 rounded-xl p-8 text-center">
            <div className="text-6xl mb-4">✅</div>
            <h2 className="text-2xl font-bold text-green-800 mb-2">Video Submitted!</h2>
            <p className="text-green-600 mb-6">Loading next video...</p>
          </div>
        </div>
      </div>
    );
  }

  // SHORT VIDEO PICKER STAGE
  if (stage === STAGES.SHORT_VIDEO_PICKER) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="mb-8 flex items-center justify-between">
            <button 
              onClick={loadNextVideo}
              className="flex items-center gap-2 text-blue-600 hover:text-blue-700 font-medium transition-colors"
            >
              <span>←</span>
              <span>Back to Queue</span>
            </button>
            <div className="px-4 py-2 bg-white rounded-lg shadow-sm border border-gray-200">
              <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                ⚡ Short Videos (Under 2 Minutes)
              </h1>
            </div>
            <div className="w-40"></div>
          </div>

          {/* Short Videos Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {shortVideos.map((shortVideo, index) => (
              <div 
                key={shortVideo.video_id}
                className="bg-white rounded-xl shadow-md hover:shadow-xl transition-all duration-300 border border-gray-200 overflow-hidden cursor-pointer"
                onClick={() => handleSelectShortVideo(shortVideo)}
              >
                <div className="relative">
                  <img
                    src={`https://img.youtube.com/vi/${shortVideo.video_id}/mqdefault.jpg`}
                    alt="Video thumbnail"
                    className="w-full h-48 object-cover"
                  />
                  <div className="absolute top-3 right-3 bg-blue-600 text-white px-3 py-1 rounded-full text-sm font-bold shadow-lg">
                    {Math.floor(shortVideo.duration_seconds / 60)}:{String(shortVideo.duration_seconds % 60).padStart(2, '0')}
                  </div>
                </div>
                
                <div className="p-5">
                  <h3 className="text-lg font-semibold text-gray-800 mb-2 line-clamp-2 hover:text-blue-600 transition-colors">
                    {shortVideo.title}
                  </h3>
                  
                  <div className="flex items-center justify-between mt-4">
                    <span className="flex items-center gap-2 text-sm text-gray-600">
                      <span>👤</span>
                      <span className="font-medium">{shortVideo.speaker_name}</span>
                    </span>
                    {(shortVideo.video_domain || shortVideo.speaker_domain) && (
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getDomainBadgeColor(shortVideo.video_domain || shortVideo.speaker_domain)}`}>
                        {(shortVideo.video_domain || shortVideo.speaker_domain).replace(/_/g, ' ').toUpperCase()}
                      </span>
                    )}
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSelectShortVideo(shortVideo);
                    }}
                    className="mt-4 w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition"
                  >
                    Select This Video
                  </button>
                </div>
              </div>
            ))}
          </div>

          {shortVideos.length === 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-8 text-center">
              <div className="text-6xl mb-4">⚡</div>
              <h2 className="text-2xl font-bold text-yellow-800 mb-2">No Short Videos Found</h2>
              <p className="text-yellow-600 mb-6">Try searching with a longer duration or check back later.</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  // PREVIEW STAGE
  if (stage === STAGES.PREVIEW) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="mb-8 flex items-center justify-between">
            <Link to="/" className="flex items-center gap-2 text-blue-600 hover:text-blue-700 font-medium transition-colors">
              <span>←</span>
              <span>Back to Dashboard</span>
            </Link>
            <div className="px-4 py-2 bg-white rounded-lg shadow-sm border border-gray-200">
              <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                🎬 Video Preview
              </h1>
            </div>
            <div className="w-40"></div>
          </div>

          <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
            {/* Video Info */}
            <div className="mb-8">
              <div className="flex items-start justify-between mb-6">
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-gray-800 mb-3">{video.title}</h2>
                  <div className="flex items-center gap-4 text-sm mb-4">
                    <span className="flex items-center gap-2 text-gray-600">
                      <span className="text-lg">👤</span>
                      <span className="font-medium">{video.speaker_name}</span>
                    </span>
                    {selectedVideoDomain && (
                      <span className={`px-4 py-1.5 rounded-full text-sm font-semibold ${getDomainBadgeColor(selectedVideoDomain)}`}>
                        {selectedVideoDomain.replace(/_/g, ' ').toUpperCase()}
                      </span>
                    )}
                  </div>

                  {/* Domain Selection */}
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      📂 Video Domain
                    </label>
                    <select
                      value={selectedVideoDomain || 'general'}
                      onChange={(e) => updateVideoDomain(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
                    >
                      <option value="food_blogger">🍳 Food Blogger</option>
                      <option value="academician">🎓 Academician</option>
                      <option value="economic">💹 Economic</option>
                      <option value="financial">💰 Financial</option>
                      <option value="motivational_speaker">💪 Motivational Speaker</option>
                      <option value="comedian">😄 Comedian</option>
                      <option value="sports_and_gaming">🎮 Sports & Gaming</option>
                      <option value="general">📋 General</option>
                      <option value="other">🔖 Other</option>
                    </select>
                    <p className="mt-2 text-xs text-gray-500">
                      Default: <span className="font-medium">{video.speaker_domain?.replace(/_/g, ' ') || 'Not set'}</span> (from speaker profile)
                    </p>
                  </div>
                </div>
                <div className="text-right bg-gradient-to-br from-blue-50 to-indigo-50 p-4 rounded-xl border border-blue-200 ml-6">
                  <div className="text-xs text-gray-600 mb-1">Duration</div>
                  <div className="text-2xl font-bold text-blue-600">
                    {Math.floor(video.duration_seconds / 60)}:{String(video.duration_seconds % 60).padStart(2, '0')}
                  </div>
                </div>
              </div>

              {/* YouTube Thumbnail */}
              <div className="mb-6 relative group overflow-hidden rounded-xl">
                <img
                  src={`https://img.youtube.com/vi/${video.video_id}/mqdefault.jpg`}
                  alt="Video thumbnail"
                  className="w-full rounded-xl shadow-lg transition-transform duration-300 group-hover:scale-105"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl"></div>
              </div>

              {/* Video Link */}
              <a
                href={video.youtube_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 font-medium bg-blue-50 px-4 py-2 rounded-lg hover:bg-blue-100 transition-all duration-200"
              >
                <span>🔗</span>
                <span>Open in YouTube</span>
                <span>↗️</span>
              </a>
            </div>

            {/* Processing History Status */}
            {checkingHistory && (
              <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center gap-2">
                  <div className="animate-spin text-blue-600 text-xl">⏳</div>
                  <span className="text-blue-800 font-medium">Checking processing history...</span>
                </div>
              </div>
            )}

            {processingHistory && processingHistory.already_processed && (
              <div className="mb-6 p-6 bg-gradient-to-r from-yellow-50 to-orange-50 border-2 border-yellow-300 rounded-xl shadow-sm">
                <div className="flex items-start gap-3 mb-4">
                  <span className="text-3xl">⚠️</span>
                  <div className="flex-1">
                    <h3 className="text-lg font-bold text-yellow-900 mb-2">Video Already Processed!</h3>
                    <p className="text-sm text-yellow-800 mb-3">
                      This video has been processed before. You can skip it or process it again with different settings.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-4">
                  {/* Database Status */}
                  <div className="bg-white rounded-lg p-4 border border-yellow-200">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xl">💾</span>
                      <h4 className="font-semibold text-gray-800">Database</h4>
                    </div>
                    {processingHistory.database.exists ? (
                      <div className="space-y-1 text-sm">
                        <div className="flex items-center gap-2">
                          <span className="text-green-600 font-bold">✓</span>
                          <span className="text-gray-700">Status: <span className="font-medium text-green-600">{processingHistory.database.status}</span></span>
                        </div>
                        {processingHistory.database.chunks_created && (
                          <div className="text-gray-600">
                            Chunks: {processingHistory.database.chunks_passed}/{processingHistory.database.chunks_created} passed
                          </div>
                        )}
                        {processingHistory.database.completed_at && (
                          <div className="text-gray-500 text-xs">
                            Completed: {new Date(processingHistory.database.completed_at).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-sm text-gray-500">No database record</div>
                    )}
                  </div>

                  {/* Processed.json Status */}
                  <div className="bg-white rounded-lg p-4 border border-yellow-200">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xl">📄</span>
                      <h4 className="font-semibold text-gray-800">Pipeline Cache</h4>
                    </div>
                    {processingHistory.processed_json.exists ? (
                      <div className="space-y-1 text-sm">
                        <div className="flex items-center gap-2">
                          <span className="text-green-600 font-bold">✓</span>
                          <span className="text-gray-700">Found in processed.json</span>
                        </div>
                        {processingHistory.processed_json.chunks && (
                          <div className="text-gray-600">
                            {processingHistory.processed_json.chunks} chunks cached
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-sm text-gray-500">Not in cache</div>
                    )}
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3">
                  <button
                    onClick={handleSkipVideo}
                    className="flex-1 px-4 py-3 bg-white hover:bg-gray-50 text-gray-700 font-semibold rounded-lg border-2 border-gray-300 transition-all shadow-sm hover:shadow"
                  >
                    ⏭️ Skip to Next Video
                  </button>
                  <button
                    onClick={() => setProcessingHistory(null)}
                    className="flex-1 px-4 py-3 bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 text-white font-semibold rounded-lg transition-all shadow-md hover:shadow-lg"
                  >
                    🔄 Process Again Anyway
                  </button>
                </div>
              </div>
            )}

            {processingHistory && !processingHistory.already_processed && (
              <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center gap-2">
                  <span className="text-xl">✨</span>
                  <span className="text-green-800 font-medium">Fresh video - Never processed before</span>
                </div>
              </div>
            )}

            {/* Processing Preset Selection */}
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">Choose Processing Quality</h3>
              <div className="space-y-3">
                {presets.map((preset) => (
                  <label
                    key={preset.value}
                    className={`block p-4 border-2 rounded-lg cursor-pointer transition ${
                      selectedPreset === preset.value
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <input
                      type="radio"
                      name="preset"
                      value={preset.value}
                      checked={selectedPreset === preset.value}
                      onChange={(e) => setSelectedPreset(e.target.value)}
                      className="mr-3"
                    />
                    <span className="font-semibold text-gray-800">{preset.label}</span>
                    <p className="text-sm text-gray-600 ml-7">{preset.description}</p>
                  </label>
                ))}
              </div>
            </div>

            {/* Transcription Model Selection */}
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">Transcription Model</h3>
              <div className="flex gap-3">
                <label
                  className={`flex-1 p-3 border-2 rounded-lg cursor-pointer transition text-center ${
                    selectedTranscriptionModel === 'google'
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="transcription"
                    value="google"
                    checked={selectedTranscriptionModel === 'google'}
                    onChange={(e) => setSelectedTranscriptionModel(e.target.value)}
                    className="hidden"
                  />
                  <div className="font-semibold text-gray-800 text-sm">🎤 Google</div>
                  <p className="text-xs text-gray-600 mt-1">Fast & Accurate</p>
                </label>
                
                <label
                  className={`flex-1 p-3 border-2 rounded-lg cursor-pointer transition text-center ${
                    selectedTranscriptionModel === 'whisper'
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="transcription"
                    value="whisper"
                    checked={selectedTranscriptionModel === 'whisper'}
                    onChange={(e) => setSelectedTranscriptionModel(e.target.value)}
                    className="hidden"
                  />
                  <div className="font-semibold text-gray-800 text-sm">🤖 Whisper</div>
                  <p className="text-xs text-gray-600 mt-1">Local Processing</p>
                </label>

                <label
                  className={`flex-1 p-3 border-2 rounded-lg cursor-pointer transition text-center ${
                    selectedTranscriptionModel === 'both'
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="transcription"
                    value="both"
                    checked={selectedTranscriptionModel === 'both'}
                    onChange={(e) => setSelectedTranscriptionModel(e.target.value)}
                    className="hidden"
                  />
                  <div className="font-semibold text-gray-800 text-sm">🔀 Both</div>
                  <p className="text-xs text-gray-600 mt-1">Compare Results</p>
                </label>
              </div>
            </div>

            {/* Warnings */}
            {video.times_rejected > 0 && (
              <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-center gap-2 text-yellow-800">
                  <span>⚠️</span>
                  <span className="font-medium">
                    This video has been rejected {video.times_rejected} time(s) before
                  </span>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-4">
              <button
                onClick={handleClaimVideo}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white font-medium py-3 px-6 rounded-lg transition"
              >
                ✅ Claim & Process This Video
              </button>
              <button
                onClick={handleSkipVideo}
                className="bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium py-3 px-6 rounded-lg transition"
              >
                Skip
              </button>
              <button
                onClick={handleSearchShortVideos}
                className="bg-blue-500 hover:bg-blue-600 text-white font-medium py-3 px-6 rounded-lg transition flex items-center gap-2"
                title="Find short videos for quick testing"
              >
                <span>⚡</span>
                <span>Short</span>
              </button>
            </div>

            {/* Estimated Time */}
            <div className="mt-4 text-center text-sm text-gray-600">
              ⏱️ Estimated processing time: ~15-20 minutes
            </div>
          </div>
        </div>
      </div>
    );
  }

  // PROCESSING STAGE
  if (stage === STAGES.PROCESSING) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
            <div className="mb-8">
              <div className="flex items-center gap-3 mb-3">
                <span className="text-3xl">⏳</span>
                <h2 className="text-3xl font-bold text-gray-800">Processing Video</h2>
              </div>
              <p className="text-gray-600 text-lg">{video.title}</p>
            </div>

            {/* Progress Bar */}
            <div className="mb-10">
              <div className="flex justify-between items-center text-sm font-medium text-gray-700 mb-3">
                <span className="flex items-center gap-2">
                  <span className="text-xl">🚀</span>
                  <span>Processing Progress</span>
                  {processingProgress < 30 && <span className="text-xs text-gray-500">(Downloading...)</span>}
                  {processingProgress >= 30 && processingProgress < 85 && <span className="text-xs text-gray-500">(Processing with Docker...)</span>}
                  {processingProgress >= 85 && processingProgress < 100 && <span className="text-xs text-gray-500">(Finalizing...)</span>}
                </span>
                <span className="text-3xl font-bold text-blue-600">{processingProgress}%</span>
              </div>
              <div className="w-full bg-gray-300 rounded-full h-6 shadow-inner">
                <div
                  className="bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 h-6 rounded-full transition-all duration-500 shadow-lg relative overflow-hidden"
                  style={{ width: `${processingProgress}%` }}
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-30 animate-shimmer"></div>
                </div>
              </div>
              
              {/* Step indicators */}
              <div className="flex justify-between mt-3 text-xs text-gray-600">
                <span className={processingProgress >= 10 ? 'text-blue-600 font-semibold' : ''}>📥 Download</span>
                <span className={processingProgress >= 30 ? 'text-blue-600 font-semibold' : ''}>🐳 Docker Pipeline</span>
                <span className={processingProgress >= 85 ? 'text-blue-600 font-semibold' : ''}>💾 Save Results</span>
                <span className={processingProgress >= 100 ? 'text-green-600 font-semibold' : ''}>✅ Complete</span>
              </div>
            </div>

            {/* Processing Logs */}
            <div className="mb-8">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xl">📝</span>
                <h3 className="font-semibold text-gray-800">Processing Log</h3>
                <span className="text-xs text-gray-500 ml-auto">Live output from Docker container</span>
              </div>
              <div className="bg-gray-900 rounded-xl p-6 font-mono text-sm text-green-400 h-96 overflow-y-auto shadow-inner border-2 border-gray-800">
              {processingLogs.map((log, index) => {
                // Color code different types of log messages
                let logColor = 'text-green-400';
                let prefix = '$';
                
                if (log.includes('ERROR') || log.includes('Failed') || log.includes('Error')) {
                  logColor = 'text-red-400';
                  prefix = '✗';
                } else if (log.includes('WARNING') || log.includes('Warning')) {
                  logColor = 'text-yellow-400';
                  prefix = '⚠';
                } else if (log.includes('Step ') || log.includes('Starting') || log.includes('Running')) {
                  logColor = 'text-blue-400';
                  prefix = '▶';
                } else if (log.includes('✅') || log.includes('complete') || log.includes('Complete') || log.includes('success') || log.includes('Success')) {
                  logColor = 'text-green-300';
                  prefix = '✓';
                } else if (log.includes('INFO')) {
                  logColor = 'text-cyan-400';
                  prefix = 'ℹ';
                }
                
                return (
                  <div key={index} className={`mb-1 flex items-start gap-2 ${logColor}`}>
                    <span className="text-gray-500 flex-shrink-0">{prefix}</span>
                    <span className="flex-1 whitespace-pre-wrap break-words">{log}</span>
                  </div>
                );
              })}
              {processingProgress < 100 && (
                <div className="flex items-center gap-2 mt-2">
                  <div className="animate-pulse text-green-400">▊</div>
                  <span className="text-gray-400 text-xs">Processing...</span>
                </div>
              )}
            </div>
            </div>

            <div className="mt-8 p-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl text-center">
              <p className="text-gray-700 font-medium mb-2">
                ⏳ This may take 15-20 minutes. Feel free to grab a coffee!
              </p>
              <p className="text-sm text-gray-600">
                🐳 Processing is happening on your local machine via Docker container.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // CHUNK REVIEW STAGE
  if (stage === STAGES.CHUNK_REVIEW) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-white rounded-xl shadow-md p-8">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold text-gray-800 mb-2">Review Processed Chunks</h2>
                <p className="text-gray-600">{video.title}</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-600">Total Chunks</p>
                <p className="text-3xl font-bold text-blue-600">{processedChunks.length}</p>
              </div>
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-4 gap-4 mb-8">
              <div className="bg-blue-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Total Created</p>
                <p className="text-2xl font-bold text-blue-600">{results?.chunks_created || 0}</p>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Passed SyncNet</p>
                <p className="text-2xl font-bold text-green-600">{results?.chunks_passed_sync || 0}</p>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Usable Duration</p>
                <p className="text-2xl font-bold text-purple-600">{((results?.usable_duration_seconds || 0) / 60).toFixed(1)}m</p>
              </div>
              <div className="bg-orange-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600 mb-1">Total Size</p>
                <p className="text-2xl font-bold text-orange-600">{(results?.total_size_mb || 0).toFixed(1)} MB</p>
              </div>
            </div>

            {/* Debug Info */}
            {processedChunks.length === 0 && (
              <div className="mb-6 p-4 bg-yellow-50 border-2 border-yellow-300 rounded-lg">
                <div className="mb-2">
                  <span className="text-xl">🔍</span>
                  <span className="font-bold text-yellow-800 ml-2">Debug Information</span>
                </div>
                <div className="text-sm text-gray-700 space-y-1">
                  <p><strong>Video ID:</strong> {video.video_id}</p>
                  <p><strong>Storage Path:</strong> {results?.storage_path || 'Not set'}</p>
                  <p><strong>Chunks in state:</strong> {processedChunks.length}</p>
                  <button
                    onClick={async () => {
                      console.log('🔄 Manual chunk fetch for:', video.video_id);
                      try {
                        const response = await fetch(
                          `http://localhost:5000/api/videos/${video.video_id}/chunks`,
                          { credentials: 'include' }
                        );
                        console.log('Response status:', response.status);
                        const data = await response.json();
                        console.log('Response data:', data);
                        if (response.ok && data.chunks) {
                          setProcessedChunks(data.chunks);
                          alert(`Loaded ${data.chunks.length} chunks!`);
                        } else {
                          alert(`Failed: ${data.error || 'Unknown error'}`);
                        }
                      } catch (error) {
                        console.error('Error:', error);
                        alert('Error: ' + error.message);
                      }
                    }}
                    className="mt-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium"
                  >
                    🔄 Retry Loading Chunks
                  </button>
                </div>
              </div>
            )}

            {/* Chunks Grid */}
            <div className="grid grid-cols-1 gap-6 mb-8">
              {processedChunks.map((chunk, index) => {
                const isMarkedForDeletion = chunksToDelete.has(chunk.chunk_id);
                const currentFormat = selectedFormat[chunk.chunk_id] || 'normal';
                
                return (
                  <div 
                    key={chunk.chunk_id} 
                    className={`bg-white rounded-xl p-6 border-2 transition-all shadow-md ${
                      isMarkedForDeletion 
                        ? 'border-red-300 bg-red-50 opacity-60' 
                        : 'border-gray-200 hover:border-blue-400'
                    }`}
                  >
                    {/* Header */}
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <span className="text-lg font-bold text-gray-800">Chunk {index + 1}</span>
                        {isMarkedForDeletion && (
                          <span className="text-xs bg-red-100 text-red-700 px-3 py-1 rounded-full font-semibold">
                            ❌ Marked for Deletion
                          </span>
                        )}
                      </div>
                      <div className="flex gap-2">
                        {chunk.has_audio && <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded font-medium">🎵 Audio</span>}
                        {chunk.has_cropped && <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded font-medium">✂️ Cropped</span>}
                        {chunk.has_bbox && <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded font-medium">📦 BBox</span>}
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      {/* Video Preview Section */}
                      <div>
                        {/* Format Selector */}
                        <div className="mb-3 flex gap-2">
                          <button
                            onClick={() => setSelectedFormat(prev => ({ ...prev, [chunk.chunk_id]: 'normal' }))}
                            className={`flex-1 px-3 py-2 text-sm font-medium rounded-lg transition-all ${
                              currentFormat === 'normal'
                                ? 'bg-blue-600 text-white shadow-md'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                          >
                            📹 Normal
                          </button>
                          {chunk.has_cropped && (
                            <button
                              onClick={() => setSelectedFormat(prev => ({ ...prev, [chunk.chunk_id]: 'cropped' }))}
                              className={`flex-1 px-3 py-2 text-sm font-medium rounded-lg transition-all ${
                                currentFormat === 'cropped'
                                  ? 'bg-blue-600 text-white shadow-md'
                                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                              }`}
                            >
                              ✂️ Cropped
                            </button>
                          )}
                          {chunk.has_bbox && (
                            <button
                              onClick={() => setSelectedFormat(prev => ({ ...prev, [chunk.chunk_id]: 'bbox' }))}
                              className={`flex-1 px-3 py-2 text-sm font-medium rounded-lg transition-all ${
                                currentFormat === 'bbox'
                                  ? 'bg-blue-600 text-white shadow-md'
                                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                              }`}
                            >
                              📦 BBox
                            </button>
                          )}
                        </div>
                        
                        {/* Video Player */}
                        <div className="bg-black rounded-lg overflow-hidden mb-3">
                          <video 
                            controls 
                            className="w-full"
                            src={`http://localhost:5000${
                              currentFormat === 'cropped' ? chunk.cropped_url :
                              currentFormat === 'bbox' ? chunk.bbox_url :
                              chunk.video_url
                            }`}
                            style={{ maxHeight: '300px' }}
                            key={currentFormat}
                          >
                            Your browser does not support the video tag.
                          </video>
                        </div>
                        
                        {/* Quality Indicators */}
                        <div className="flex items-center gap-3 text-xs">
                          <span className="flex items-center gap-1">
                            <span>{chunk.has_audio ? '✅' : '❌'}</span>
                            <span className="text-gray-600">Audio</span>
                          </span>
                          <span className="flex items-center gap-1">
                            <span>{chunk.has_cropped ? '✅' : '❌'}</span>
                            <span className="text-gray-600">Cropped</span>
                          </span>
                          <span className="flex items-center gap-1">
                            <span>{chunk.has_bbox ? '✅' : '❌'}</span>
                            <span className="text-gray-600">BBox</span>
                          </span>
                          <span className="flex items-center gap-1">
                            <span>{chunk.transcription ? '✅' : '❌'}</span>
                            <span className="text-gray-600">Transcript</span>
                          </span>
                        </div>
                      </div>
                      
                      {/* Transcription & Actions Section */}
                      <div className="flex flex-col">
                        {/* Transcription */}
                        <div className="flex-1 mb-4">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-sm font-semibold text-gray-700">📝 Transcription</span>
                          </div>
                          {chunk.transcription ? (
                            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 max-h-40 overflow-y-auto">
                              <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                                {chunk.transcription}
                              </p>
                            </div>
                          ) : (
                            <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                              <p className="text-sm text-yellow-700">⚠️ No transcription available</p>
                            </div>
                          )}
                        </div>
                        
                        {/* Keep/Delete Actions */}
                        <div className="flex gap-3">
                          {isMarkedForDeletion ? (
                            <button
                              onClick={() => {
                                const newSet = new Set(chunksToDelete);
                                newSet.delete(chunk.chunk_id);
                                setChunksToDelete(newSet);
                              }}
                              className="flex-1 px-4 py-3 bg-green-500 hover:bg-green-600 text-white font-semibold rounded-lg transition-all shadow-md"
                            >
                              ✅ Keep This Chunk
                            </button>
                          ) : (
                            <>
                              <button
                                onClick={() => {
                                  const newSet = new Set(chunksToDelete);
                                  newSet.add(chunk.chunk_id);
                                  setChunksToDelete(newSet);
                                }}
                                className="flex-1 px-4 py-3 bg-red-100 hover:bg-red-200 text-red-700 font-semibold rounded-lg transition-all border-2 border-red-300"
                              >
                                ❌ Delete
                              </button>
                              <button
                                className="flex-1 px-4 py-3 bg-green-100 hover:bg-green-200 text-green-700 font-semibold rounded-lg transition-all border-2 border-green-300"
                              >
                                ✅ Keep
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Deletion Summary */}
            {chunksToDelete.size > 0 && (
              <div className="mb-6 p-4 bg-red-50 border-2 border-red-300 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">⚠️</span>
                    <div>
                      <p className="font-semibold text-red-800">
                        {chunksToDelete.size} chunk(s) marked for deletion
                      </p>
                      <p className="text-sm text-red-600">
                        These chunks will be excluded from the final dataset
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setChunksToDelete(new Set())}
                    className="px-4 py-2 bg-white hover:bg-gray-100 text-red-700 font-medium rounded-lg transition-all border border-red-300"
                  >
                    Clear All
                  </button>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex justify-between items-center pt-6 border-t border-gray-200">
              <button
                onClick={() => setStage(STAGES.PROCESSING)}
                className="px-6 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold rounded-lg transition-all"
              >
                ← Back to Logs
              </button>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <p className="text-sm text-gray-600">Final Chunks</p>
                  <p className="text-2xl font-bold text-green-600">
                    {processedChunks.length - chunksToDelete.size} / {processedChunks.length}
                  </p>
                </div>
                <button
                  onClick={() => {
                    if (window.confirm('Are you sure you want to reject all chunks and reprocess?')) {
                      setChunksToDelete(new Set());
                      setStage(STAGES.PREVIEW);
                    }
                  }}
                  className="px-6 py-3 bg-red-100 hover:bg-red-200 text-red-700 font-semibold rounded-lg transition-all"
                >
                  ❌ Reject & Reprocess
                </button>
                <button
                  onClick={() => {
                    // Update results with manual approval/rejection counts
                    const updatedResults = {
                      ...results,
                      chunks_manually_approved: processedChunks.length - chunksToDelete.size,
                      chunks_manually_rejected: chunksToDelete.size
                    };
                    setResults(updatedResults);
                    setStage(STAGES.REVIEWING);
                  }}
                  className="px-8 py-3 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white font-semibold rounded-lg shadow-lg transition-all"
                  disabled={processedChunks.length - chunksToDelete.size === 0}
                >
                  ✅ Approve {processedChunks.length - chunksToDelete.size} Chunks
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // REVIEWING STAGE
  if (stage === STAGES.REVIEWING) {
    const retentionRate = (results.chunks_passed_sync / results.chunks_created * 100).toFixed(1);
    const usableMinutes = (results.usable_duration_seconds / 60).toFixed(1);

    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-xl shadow-md p-8">
            <h2 className="text-2xl font-bold text-gray-800 mb-2">Review Results</h2>
            <p className="text-gray-600 mb-6">{video.title}</p>

            {/* Results Summary */}
            <div className="mb-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
              <h3 className="font-semibold text-blue-900 mb-4">Processing Summary</h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div>
                  <div className="text-2xl font-bold text-blue-600">{results.chunks_created}</div>
                  <div className="text-sm text-gray-600">Chunks Created</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-green-600">{results.chunks_passed_sync}</div>
                  <div className="text-sm text-gray-600">Passed Filters</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-emerald-600">{results.chunks_manually_approved || 0}</div>
                  <div className="text-sm text-gray-600">Manually Approved</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-red-600">{results.chunks_manually_rejected || 0}</div>
                  <div className="text-sm text-gray-600">Manually Rejected</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-indigo-600">{usableMinutes}m</div>
                  <div className="text-sm text-gray-600">Usable Duration</div>
                </div>
              </div>
              
              {results.chunks_manually_rejected > 0 && (
                <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-sm text-yellow-800">
                    ⚠️ You manually rejected {results.chunks_manually_rejected} chunk(s) during review. 
                    Final count: <span className="font-bold">{results.chunks_manually_approved}</span> chunks will be included in the dataset.
                  </p>
                </div>
              )}
            </div>

            {/* Quality Metrics */}
            <div className="mb-8">
              <h3 className="font-semibold text-gray-800 mb-4">Quality Metrics</h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Sync Score</span>
                    <span className="font-medium">{results.avg_sync_score.toFixed(2)} (Range: {results.min_sync_score.toFixed(1)} - {results.max_sync_score.toFixed(1)})</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        results.avg_sync_score >= 7.5 ? 'bg-green-500' : 
                        results.avg_sync_score >= 6.0 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${(results.avg_sync_score / 10) * 100}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Face Presence</span>
                    <span className="font-medium">{(results.avg_face_presence * 100).toFixed(1)}% (Range: {(results.min_face_presence * 100).toFixed(0)}% - {(results.max_face_presence * 100).toFixed(0)}%)</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        results.avg_face_presence >= 0.90 ? 'bg-green-500' : 
                        results.avg_face_presence >= 0.80 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${results.avg_face_presence * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Quality Rating */}
            <div className="mb-8">
              <h3 className="font-semibold text-gray-800 mb-4">Rate Quality (1-5 stars)</h3>
              <div className="space-y-4">
                {['audio_quality', 'video_quality', 'transcription_quality', 'overall_quality'].map((field) => (
                  <div key={field}>
                    <label className="block text-sm text-gray-600 mb-2 capitalize">
                      {field.replace(/_/g, ' ')}
                    </label>
                    <div className="flex gap-2">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          onClick={() => updateReviewField(field, star)}
                          className={`text-3xl ${
                            reviewData[field] >= star ? 'text-yellow-400' : 'text-gray-300'
                          }`}
                        >
                          ⭐
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Issue Checkboxes */}
            <div className="mb-8">
              <h3 className="font-semibold text-gray-800 mb-4">Report Issues (if any)</h3>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { field: 'wrong_language', label: '🗣️ Wrong Language' },
                  { field: 'poor_audio', label: '🔇 Poor Audio Quality' },
                  { field: 'no_face', label: '👤 No Face Visible' },
                  { field: 'bad_sync', label: '🔄 Bad Audio-Visual Sync' },
                  { field: 'wrong_content', label: '⚠️ Inappropriate Content' }
                ].map(({ field, label }) => (
                  <label key={field} className="flex items-center gap-2 p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
                    <input
                      type="checkbox"
                      checked={reviewData[field]}
                      onChange={(e) => {
                        updateReviewField(field, e.target.checked);
                        updateReviewField('has_issues', true);
                      }}
                      className="w-4 h-4"
                    />
                    <span className="text-sm">{label}</span>
                  </label>
                ))}
              </div>

              {reviewData.has_issues && (
                <div className="mt-4">
                  <label className="block text-sm text-gray-600 mb-2">Additional Notes</label>
                  <textarea
                    value={reviewData.issue_notes}
                    onChange={(e) => updateReviewField('issue_notes', e.target.value)}
                    placeholder="Describe the issues..."
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    rows="3"
                  />
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-4">
              <button
                onClick={() => handleReview('approved')}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white font-medium py-3 px-6 rounded-lg transition"
              >
                ✅ Approve & Submit
              </button>
              <button
                onClick={() => handleReview('flagged')}
                className="flex-1 bg-yellow-500 hover:bg-yellow-600 text-white font-medium py-3 px-6 rounded-lg transition"
              >
                🚩 Flag for Review
              </button>
              <button
                onClick={() => handleReview('rejected')}
                className="flex-1 bg-red-600 hover:bg-red-700 text-white font-medium py-3 px-6 rounded-lg transition"
              >
                ❌ Reject Video
              </button>
            </div>

            <div className="mt-4 text-center text-sm text-gray-600">
              💡 Approve if quality is acceptable. Flag if uncertain. Reject if unusable.
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}

export default VideoQueue;