import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { logout, getStudentStats, getOverallStats } from '../api';

function Dashboard({ user, onLogout }) {
  const [studentStats, setStudentStats] = useState(null);
  const [overallStats, setOverallStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const [student, overall] = await Promise.all([
        getStudentStats(),
        getOverallStats()
      ]);
      setStudentStats(student.data);
      setOverallStats(overall.data);
    } catch (error) {
      console.error('Error loading stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    onLogout();
  };

  if (loading) {
    return <div className="p-8">Loading...</div>;
  }

  const { total, today } = studentStats || {};
  const { jobs, dataset } = overallStats || {};

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <nav className="bg-white shadow-md border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <div className="text-3xl">🎬</div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                  Bengali Dataset Manager
                </h1>
                <p className="text-xs text-gray-500">Audio-Visual Speech Dataset Platform</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-xs text-gray-500">Logged in as</p>
                <p className="font-semibold text-gray-800">
                  👤 {user.student_name || user.student_id}
                </p>
              </div>
              <button
                onClick={handleLogout}
                className="bg-red-50 hover:bg-red-100 text-red-600 font-medium px-4 py-2 rounded-lg transition-all duration-200 border border-red-200"
              >
                🚪 Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Welcome Message */}
        <div className="bg-gradient-to-r from-blue-500 to-indigo-600 rounded-2xl p-8 mb-8 shadow-xl text-white">
          <h2 className="text-3xl font-bold mb-3">
            Welcome back, {user.student_name || user.student_id}! 👋
          </h2>
          <p className="text-blue-100 text-lg">
            Ready to contribute? Let's process some videos and build an amazing dataset together! 🚀
          </p>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <Link
            to="/queue"
            className="group bg-gradient-to-br from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white p-10 rounded-2xl shadow-xl transition-all duration-300 transform hover:scale-105 hover:shadow-2xl"
          >
            <div className="text-5xl mb-4 transform group-hover:scale-110 transition-transform duration-300">🎬</div>
            <h3 className="text-3xl font-bold mb-3">Process Next Video</h3>
            <p className="text-green-100 text-lg">Claim and process a video from the queue</p>
            <div className="mt-4 flex items-center gap-2 text-green-50 font-medium">
              <span>Get Started</span>
              <span className="transform group-hover:translate-x-2 transition-transform duration-300">→</span>
            </div>
          </Link>

          <Link
            to="/stats"
            className="group bg-gradient-to-br from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white p-10 rounded-2xl shadow-xl transition-all duration-300 transform hover:scale-105 hover:shadow-2xl"
          >
            <div className="text-5xl mb-4 transform group-hover:scale-110 transition-transform duration-300">📊</div>
            <h3 className="text-3xl font-bold mb-3">View Statistics</h3>
            <p className="text-blue-100 text-lg">Check your progress and dataset stats</p>
            <div className="mt-4 flex items-center gap-2 text-blue-50 font-medium">
              <span>View Details</span>
              <span className="transform group-hover:translate-x-2 transition-transform duration-300">→</span>
            </div>
          </Link>
        </div>

        {/* Your Stats Today */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-8 border border-gray-100">
          <div className="flex items-center gap-3 mb-6">
            <span className="text-3xl">📅</span>
            <h3 className="text-2xl font-bold text-gray-800">Today's Progress</h3>
          </div>
          <div className="grid grid-cols-3 gap-6">
            <div className="bg-gradient-to-br from-green-50 to-emerald-50 p-6 rounded-xl border border-green-200">
              <div className="text-4xl font-bold text-green-600 mb-2">
                {today?.completed_today || 0}
              </div>
              <div className="text-sm font-medium text-gray-700">Videos Completed</div>
              <div className="text-xs text-gray-500 mt-1">⬆️ Great work!</div>
            </div>
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 p-6 rounded-xl border border-blue-200">
              <div className="text-4xl font-bold text-blue-600 mb-2">
                {(today?.hours_today || 0).toFixed(1)}h
              </div>
              <div className="text-sm font-medium text-gray-700">Hours Processed</div>
              <div className="text-xs text-gray-500 mt-1">⏱️ Time contribution</div>
            </div>
            <div className="bg-gradient-to-br from-red-50 to-pink-50 p-6 rounded-xl border border-red-200">
              <div className="text-4xl font-bold text-red-600 mb-2">
                {today?.rejected_today || 0}
              </div>
              <div className="text-sm font-medium text-gray-700">Videos Rejected</div>
              <div className="text-xs text-gray-500 mt-1">🚫 Quality control</div>
            </div>
          </div>
        </div>

        {/* Overall Stats */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-8 border border-gray-100">
          <div className="flex items-center gap-3 mb-6">
            <span className="text-3xl">📈</span>
            <h3 className="text-2xl font-bold text-gray-800">Your Total Contribution</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="text-center p-4 bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl">
              <div className="text-3xl font-bold text-gray-800 mb-1">
                {total?.jobs_completed || 0}
              </div>
              <div className="text-sm text-gray-600 font-medium">Completed</div>
            </div>
            <div className="text-center p-4 bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl">
              <div className="text-3xl font-bold text-gray-800 mb-1">
                {total?.jobs_rejected || 0}
              </div>
              <div className="text-sm text-gray-600 font-medium">Rejected</div>
            </div>
            <div className="text-center p-4 bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl">
              <div className="text-3xl font-bold text-gray-800 mb-1">
                {(total?.total_hours_processed || 0).toFixed(1)}h
              </div>
              <div className="text-sm text-gray-600 font-medium">Total Hours</div>
            </div>
            <div className="text-center p-4 bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl">
              <div className="text-3xl font-bold text-gray-800 mb-1">
                {(total?.avg_processing_time_minutes || 0).toFixed(0)}m
              </div>
              <div className="text-sm text-gray-600 font-medium">Avg Time/Video</div>
            </div>
          </div>
        </div>

        {/* Dataset Progress */}
        <div className="bg-white rounded-2xl shadow-lg p-8 border border-gray-100">
          <div className="flex items-center gap-3 mb-6">
            <span className="text-3xl">🎯</span>
            <h3 className="text-2xl font-bold text-gray-800">Dataset Progress</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {jobs?.pending || 0}
              </div>
              <div className="text-sm text-gray-600">Pending</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-600">
                {jobs?.processing || 0}
              </div>
              <div className="text-sm text-gray-600">Processing</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {jobs?.completed || 0}
              </div>
              <div className="text-sm text-gray-600">Completed</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {(dataset?.total_hours || 0).toFixed(0)}h
              </div>
              <div className="text-sm text-gray-600">Total Hours</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-indigo-600">
                {dataset?.total_chunks || 0}
              </div>
              <div className="text-sm text-gray-600">Total Chunks</div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="mt-8 p-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl">
            <div className="flex justify-between items-center text-sm font-medium text-gray-700 mb-3">
              <span className="flex items-center gap-2">
                <span className="text-xl">🚀</span>
                <span>Progress to 1000 hours goal</span>
              </span>
              <span className="text-2xl font-bold text-blue-600">{((dataset?.total_hours || 0) / 1000 * 100).toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-300 rounded-full h-4 shadow-inner">
              <div
                className="bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 h-4 rounded-full transition-all duration-1000 shadow-lg relative overflow-hidden"
                style={{ width: `${Math.min((dataset?.total_hours || 0) / 1000 * 100, 100)}%` }}
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-30 animate-shimmer"></div>
              </div>
            </div>
            <div className="mt-3 text-sm text-gray-600 text-center">
              {(dataset?.total_hours || 0).toFixed(1)} / 1000 hours completed
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;