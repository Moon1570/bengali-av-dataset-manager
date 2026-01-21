import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getStudentStats, getOverallStats, getDomainStats } from '../api';

function Stats({ user }) {
  const [studentStats, setStudentStats] = useState(null);
  const [overallStats, setOverallStats] = useState(null);
  const [domainStats, setDomainStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    loadAllStats();
    // Refresh every 30 seconds
    const interval = setInterval(loadAllStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadAllStats = async () => {
    try {
      const [student, overall, domains] = await Promise.all([
        getStudentStats(),
        getOverallStats(),
        getDomainStats()
      ]);
      setStudentStats(student.data);
      setOverallStats(overall.data);
      setDomainStats(domains.data.domains);
    } catch (error) {
      console.error('Error loading stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const getDomainIcon = (domain) => {
    const icons = {
      'food_blogger': '🍳',
      'academician': '🎓',
      'economic': '📈',
      'financial': '💰',
      'motivational_speaker': '💪',
      'comedian': '😄',
      'sports_and_gaming': '🎮',
      'general': '📺',
      'other': '🎬'
    };
    return icons[domain] || '📺';
  };

  const getDomainColor = (domain) => {
    const colors = {
      'food_blogger': 'from-yellow-400 to-orange-500',
      'academician': 'from-blue-400 to-blue-600',
      'economic': 'from-green-400 to-green-600',
      'financial': 'from-purple-400 to-purple-600',
      'motivational_speaker': 'from-pink-400 to-pink-600',
      'comedian': 'from-orange-400 to-red-500',
      'sports_and_gaming': 'from-red-400 to-red-600',
      'general': 'from-gray-400 to-gray-600'
    };
    return colors[domain] || colors['general'];
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-xl text-gray-600">Loading statistics...</div>
        </div>
      </div>
    );
  }

  const { total, today } = studentStats || {};
  const { jobs, dataset, workers } = overallStats || {};

  // Calculate targets
  const targetHours = 1000;
  const daysRemaining = 10;
  const hoursProgress = (dataset?.total_hours || 0);
  const hoursPerDay = hoursProgress / (10 - daysRemaining || 1);
  const projectedTotal = hoursProgress + (hoursPerDay * daysRemaining);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <Link to="/" className="text-blue-600 hover:text-blue-700 font-medium">
              ← Back to Dashboard
            </Link>
            <h1 className="text-2xl font-bold text-gray-800">Statistics</h1>
            <button
              onClick={loadAllStats}
              className="text-blue-600 hover:text-blue-700 font-medium"
            >
              🔄 Refresh
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Tabs */}
        <div className="mb-8 bg-white rounded-lg shadow-sm p-2 flex gap-2">
          {['overview', 'personal', 'domains'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-3 px-4 rounded-lg font-medium transition capitalize ${
                activeTab === tab
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Target Progress */}
            <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-xl shadow-lg p-8 text-white">
              <h2 className="text-2xl font-bold mb-6">🎯 Mission: 1000 Hours in 10 Days</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <div>
                  <div className="text-3xl font-bold">{hoursProgress.toFixed(1)}h</div>
                  <div className="text-blue-100">Current Progress</div>
                </div>
                <div>
                  <div className="text-3xl font-bold">{daysRemaining}</div>
                  <div className="text-blue-100">Days Remaining</div>
                </div>
                <div>
                  <div className="text-3xl font-bold">{projectedTotal.toFixed(0)}h</div>
                  <div className="text-blue-100">Projected Total</div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>Overall Progress</span>
                  <span>{((hoursProgress / targetHours) * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-blue-400 bg-opacity-30 rounded-full h-4">
                  <div
                    className="bg-white h-4 rounded-full transition-all duration-1000"
                    style={{ width: `${Math.min((hoursProgress / targetHours) * 100, 100)}%` }}
                  />
                </div>
                <div className="mt-2 text-sm text-blue-100">
                  {hoursProgress >= targetHours
                    ? '🎉 Target achieved!'
                    : projectedTotal >= targetHours
                    ? '✅ On track to meet target'
                    : '⚠️ Need to increase pace'
                  }
                </div>
              </div>
            </div>

            {/* Key Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="bg-white rounded-xl shadow-md p-6">
                <div className="text-3xl mb-2">📹</div>
                <div className="text-3xl font-bold text-gray-800">{dataset?.total_videos || 0}</div>
                <div className="text-sm text-gray-600">Total Videos</div>
              </div>

              <div className="bg-white rounded-xl shadow-md p-6">
                <div className="text-3xl mb-2">🎬</div>
                <div className="text-3xl font-bold text-gray-800">{dataset?.total_chunks || 0}</div>
                <div className="text-sm text-gray-600">Total Chunks</div>
              </div>

              <div className="bg-white rounded-xl shadow-md p-6">
                <div className="text-3xl mb-2">👥</div>
                <div className="text-3xl font-bold text-gray-800">{dataset?.total_speakers || 0}</div>
                <div className="text-sm text-gray-600">Speakers</div>
              </div>

              <div className="bg-white rounded-xl shadow-md p-6">
                <div className="text-3xl mb-2">👨‍💻</div>
                <div className="text-3xl font-bold text-gray-800">{workers?.active_workers || 0}</div>
                <div className="text-sm text-gray-600">Active Workers</div>
              </div>
            </div>

            {/* Job Queue Status */}
            <div className="bg-white rounded-xl shadow-md p-6">
              <h3 className="text-xl font-bold text-gray-800 mb-4">Queue Status</h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">{jobs?.pending || 0}</div>
                  <div className="text-sm text-gray-600">Pending</div>
                </div>
                <div className="text-center p-4 bg-yellow-50 rounded-lg">
                  <div className="text-2xl font-bold text-yellow-600">{jobs?.processing || 0}</div>
                  <div className="text-sm text-gray-600">Processing</div>
                </div>
                <div className="text-center p-4 bg-purple-50 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">{jobs?.reviewing || 0}</div>
                  <div className="text-sm text-gray-600">Reviewing</div>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">{jobs?.completed || 0}</div>
                  <div className="text-sm text-gray-600">Completed</div>
                </div>
                <div className="text-center p-4 bg-red-50 rounded-lg">
                  <div className="text-2xl font-bold text-red-600">{jobs?.rejected || 0}</div>
                  <div className="text-sm text-gray-600">Rejected</div>
                </div>
              </div>
            </div>

            {/* Quality Metrics */}
            <div className="bg-white rounded-xl shadow-md p-6">
              <h3 className="text-xl font-bold text-gray-800 mb-4">Overall Quality</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-gray-600">Average Sync Score</span>
                    <span className="font-bold">{(dataset?.avg_sync_score || 0).toFixed(2)}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className={`h-3 rounded-full ${
                        dataset?.avg_sync_score >= 7.5 ? 'bg-green-500' :
                        dataset?.avg_sync_score >= 6.5 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${((dataset?.avg_sync_score || 0) / 10) * 100}%` }}
                    />
                  </div>
                  <div className="mt-1 text-xs text-gray-500">Target: ≥ 7.0</div>
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-gray-600">Average Face Presence</span>
                    <span className="font-bold">{((dataset?.avg_face_presence || 0) * 100).toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className={`h-3 rounded-full ${
                        dataset?.avg_face_presence >= 0.90 ? 'bg-green-500' :
                        dataset?.avg_face_presence >= 0.80 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${(dataset?.avg_face_presence || 0) * 100}%` }}
                    />
                  </div>
                  <div className="mt-1 text-xs text-gray-500">Target: ≥ 90%</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* PERSONAL TAB */}
        {activeTab === 'personal' && (
          <div className="space-y-6">
            {/* Personal Header */}
            <div className="bg-gradient-to-r from-purple-600 to-pink-600 rounded-xl shadow-lg p-8 text-white">
              <h2 className="text-2xl font-bold mb-2">Your Performance</h2>
              <p className="text-purple-100">Student ID: {user.student_id}</p>
            </div>

            {/* Today's Work */}
            <div className="bg-white rounded-xl shadow-md p-6">
              <h3 className="text-xl font-bold text-gray-800 mb-4">📅 Today's Work</h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="text-3xl font-bold text-green-600">{today?.completed_today || 0}</div>
                  <div className="text-sm text-gray-600">Videos Completed</div>
                </div>
                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <div className="text-3xl font-bold text-blue-600">{(today?.hours_today || 0).toFixed(1)}h</div>
                  <div className="text-sm text-gray-600">Hours Processed</div>
                </div>
                <div className="text-center p-4 bg-red-50 rounded-lg">
                  <div className="text-3xl font-bold text-red-600">{today?.rejected_today || 0}</div>
                  <div className="text-sm text-gray-600">Rejected</div>
                </div>
              </div>
            </div>

            {/* All-Time Stats */}
            <div className="bg-white rounded-xl shadow-md p-6">
              <h3 className="text-xl font-bold text-gray-800 mb-4">📊 All-Time Statistics</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <div className="text-2xl font-bold text-gray-800">{total?.jobs_completed || 0}</div>
                  <div className="text-sm text-gray-600">Completed</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-gray-800">{total?.jobs_rejected || 0}</div>
                  <div className="text-sm text-gray-600">Rejected</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-gray-800">{total?.jobs_failed || 0}</div>
                  <div className="text-sm text-gray-600">Failed</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-gray-800">
                    {((total?.jobs_completed || 0) / ((total?.jobs_completed || 0) + (total?.jobs_rejected || 0) + (total?.jobs_failed || 0) || 1) * 100).toFixed(0)}%
                  </div>
                  <div className="text-sm text-gray-600">Success Rate</div>
                </div>
              </div>
            </div>

            {/* Performance Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white rounded-xl shadow-md p-6">
                <h3 className="text-lg font-bold text-gray-800 mb-4">⏱️ Processing Time</h3>
                <div className="text-center">
                  <div className="text-4xl font-bold text-blue-600 mb-2">
                    {(total?.avg_processing_time_minutes || 0).toFixed(0)}
                  </div>
                  <div className="text-gray-600">Minutes per Video (Avg)</div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-md p-6">
                <h3 className="text-lg font-bold text-gray-800 mb-4">⭐ Quality Score</h3>
                <div className="text-center">
                  <div className="text-4xl font-bold text-purple-600 mb-2">
                    {(total?.avg_quality_score || 0).toFixed(1)}
                  </div>
                  <div className="text-gray-600">Average Rating (1-5)</div>
                </div>
              </div>
            </div>

            {/* Total Contribution */}
            <div className="bg-white rounded-xl shadow-md p-6">
              <h3 className="text-lg font-bold text-gray-800 mb-4">🎯 Your Contribution</h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>Total Hours Processed</span>
                    <span className="font-bold">{(total?.total_hours_processed || 0).toFixed(1)}h</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full"
                      style={{ width: `${Math.min((total?.total_hours_processed || 0) / 100 * 100, 100)}%` }}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4 mt-4">
                  <div className="text-center p-3 bg-blue-50 rounded-lg">
                    <div className="text-lg font-bold text-blue-600">
                      {((total?.total_hours_processed || 0) / (hoursProgress || 1) * 100).toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-600">Of Total Dataset</div>
                  </div>
                  <div className="text-center p-3 bg-green-50 rounded-lg">
                    <div className="text-lg font-bold text-green-600">
                      {((total?.jobs_completed || 0) / (jobs?.completed || 1) * 100).toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-600">Of All Completed</div>
                  </div>
                  <div className="text-center p-3 bg-purple-50 rounded-lg">
                    <div className="text-lg font-bold text-purple-600">
                      #{Math.floor(Math.random() * 5) + 1}
                    </div>
                    <div className="text-xs text-gray-600">Rank (Mock)</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* DOMAINS TAB */}
        {activeTab === 'domains' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-md p-6">
              <h3 className="text-xl font-bold text-gray-800 mb-6">📂 Domain Distribution</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {domainStats.map((domain) => (
                  <div
                    key={domain.domain}
                    className="border-2 border-gray-200 rounded-xl p-6 hover:border-blue-300 transition"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <span className="text-4xl">{getDomainIcon(domain.domain)}</span>
                        <div>
                          <h4 className="font-bold text-gray-800 capitalize">
                            {domain.domain.replace(/_/g, ' ')}
                          </h4>
                          <p className="text-sm text-gray-500">{domain.speaker_count} speakers</p>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Videos</span>
                        <span className="font-bold">{domain.video_count}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Chunks</span>
                        <span className="font-bold">{domain.total_chunks}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Hours</span>
                        <span className="font-bold">{domain.total_hours.toFixed(1)}h</span>
                      </div>
                      
                      <div className="pt-3 border-t">
                        <div className="text-xs text-gray-500 mb-1">Quality</div>
                        <div className="flex gap-2">
                          <div className="flex-1">
                            <div className="text-xs text-gray-600 mb-1">Sync</div>
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div
                                className={`h-2 rounded-full ${
                                  domain.avg_sync_score >= 7.5 ? 'bg-green-500' :
                                  domain.avg_sync_score >= 6.5 ? 'bg-yellow-500' : 'bg-red-500'
                                }`}
                                style={{ width: `${(domain.avg_sync_score / 10) * 100}%` }}
                              />
                            </div>
                          </div>
                          <div className="flex-1">
                            <div className="text-xs text-gray-600 mb-1">Face</div>
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div
                                className={`h-2 rounded-full ${
                                  domain.avg_face_presence >= 0.90 ? 'bg-green-500' :
                                  domain.avg_face_presence >= 0.80 ? 'bg-yellow-500' : 'bg-red-500'
                                }`}
                                style={{ width: `${domain.avg_face_presence * 100}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Progress bar */}
                    <div className="mt-4">
                      <div className="text-xs text-gray-500 mb-1">
                        {((domain.total_hours / hoursProgress) * 100).toFixed(1)}% of dataset
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`bg-gradient-to-r ${getDomainColor(domain.domain)} h-2 rounded-full`}
                          style={{ width: `${(domain.total_hours / hoursProgress) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Domain Balance Check */}
            <div className="bg-white rounded-xl shadow-md p-6">
              <h3 className="text-lg font-bold text-gray-800 mb-4">⚖️ Balance Check</h3>
              <div className="space-y-2">
                {domainStats.map((domain) => {
                  const percentage = (domain.total_hours / hoursProgress) * 100;
                  const isBalanced = percentage <= 25;
                  
                  return (
                    <div key={domain.domain} className="flex items-center gap-3">
                      <div className="w-48 text-sm capitalize">
                        {domain.domain.replace(/_/g, ' ')}
                      </div>
                      <div className="flex-1">
                        <div className="w-full bg-gray-200 rounded-full h-6 overflow-hidden">
                          <div
                            className={`h-6 rounded-full flex items-center justify-end pr-2 text-xs font-bold text-white ${
                              isBalanced ? 'bg-green-500' : 'bg-yellow-500'
                            }`}
                            style={{ width: `${percentage}%` }}
                          >
                            {percentage.toFixed(1)}%
                          </div>
                        </div>
                      </div>
                      <div className="w-16 text-right text-sm">
                        {isBalanced ? '✅' : '⚠️'}
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="mt-4 text-sm text-gray-600">
                💡 Ideal: Each domain should be ≤25% of total dataset
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Stats;