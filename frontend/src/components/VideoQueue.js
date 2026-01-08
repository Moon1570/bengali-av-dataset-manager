import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getNextVideo, claimVideo, startProcessing, submitResults, submitReview } from '../api';

// Workflow stages
const STAGES = {
  LOADING: 'loading',
  PREVIEW: 'preview',
  PROCESSING: 'processing',
  REVIEWING: 'reviewing',
  COMPLETE: 'complete',
  ERROR: 'error',
  NO_VIDEOS: 'no_videos'
};

function VideoQueue({ user }) {
  const [stage, setStage] = useState(STAGES.LOADING);
  const [video, setVideo] = useState(null);
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState('balanced');
  const [jobId, setJobId] = useState(null);
  const [error, setError] = useState('');
  
  // Processing state
  const [processingLogs, setProcessingLogs] = useState([]);
  const [processingProgress, setProcessingProgress] = useState(0);
  
  // Results state
  const [results, setResults] = useState(null);
  
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
      const response = await getNextVideo();
      setVideo(response.data.video);
      setPresets(response.data.presets);
      setSelectedPreset('balanced');
      setStage(STAGES.PREVIEW);
    } catch (error) {
      if (error.response?.status === 404) {
        setStage(STAGES.NO_VIDEOS);
      } else {
        setError(error.response?.data?.error || 'Failed to load video');
        setStage(STAGES.ERROR);
      }
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
  const maxPolls = 360; // 30 minutes (360 * 5 seconds)
  
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
      
      // Update progress
      if (data.progress) {
        console.log('📈 Progress updated:', data.progress);
        setProcessingProgress(data.progress);
      }
      
      // Update logs
      if (data.logs && data.logs.length > 0) {
        setProcessingLogs(data.logs);
      }
      
      if (data.status === 'completed') {
        clearInterval(pollInterval);
        console.log('✅ Processing complete! Results:', data.results);
        
        setProcessingProgress(100);
        setProcessingLogs(prev => [...prev, '✅ Processing complete!']);
        
        // Set results and move to review
        setResults(data.results);
        
        setTimeout(() => {
          setStage(STAGES.REVIEWING);
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
        setError('Processing timeout - took longer than 30 minutes');
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
                  <div className="flex items-center gap-4 text-sm">
                    <span className="flex items-center gap-2 text-gray-600">
                      <span className="text-lg">👤</span>
                      <span className="font-medium">{video.speaker_name}</span>
                    </span>
                    <span className={`px-4 py-1.5 rounded-full text-sm font-semibold ${getDomainBadgeColor(video.domain)}`}>
                      {video.domain.replace(/_/g, ' ').toUpperCase()}
                    </span>
                  </div>
                </div>
                <div className="text-right bg-gradient-to-br from-blue-50 to-indigo-50 p-4 rounded-xl border border-blue-200">
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
                onClick={loadNextVideo}
                className="bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium py-3 px-6 rounded-lg transition"
              >
                Skip
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
                </span>
                <span className="text-3xl font-bold text-blue-600">{processingProgress}%</span>
              </div>
              <div className="w-full bg-gray-300 rounded-full h-5 shadow-inner">
                <div
                  className="bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 h-5 rounded-full transition-all duration-500 shadow-lg relative overflow-hidden"
                  style={{ width: `${processingProgress}%` }}
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-30 animate-shimmer"></div>
                </div>
              </div>
            </div>

            {/* Processing Logs */}
            <div className="mb-8">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xl">📝</span>
                <h3 className="font-semibold text-gray-800">Processing Log</h3>
              </div>
              <div className="bg-gray-900 rounded-xl p-6 font-mono text-sm text-green-400 h-80 overflow-y-auto shadow-inner border-2 border-gray-800">
              {processingLogs.map((log, index) => (
                <div key={index} className="mb-2 flex items-start gap-2">
                  <span className="text-gray-500">$</span>
                  <span className="flex-1">{log}</span>
                </div>
              ))}
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
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <div className="text-2xl font-bold text-blue-600">{results.chunks_created}</div>
                  <div className="text-sm text-gray-600">Chunks Created</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-green-600">{results.chunks_passed_sync}</div>
                  <div className="text-sm text-gray-600">Passed Filters</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-purple-600">{retentionRate}%</div>
                  <div className="text-sm text-gray-600">Retention Rate</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-indigo-600">{usableMinutes}m</div>
                  <div className="text-sm text-gray-600">Usable Duration</div>
                </div>
              </div>
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