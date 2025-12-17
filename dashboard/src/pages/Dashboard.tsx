import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity,
  Zap,
  Award,
  Wrench,
  TrendingUp,
  Clock,
  CheckCircle,
  AlertCircle,
  FileText,
  Server
} from 'lucide-react';
import type { KurralArtifact } from '../types/kurral';

interface DashboardStats {
  totalRuns: number;
  mcpSessions: number;
  avgARSScore: number;
  totalToolCalls: number;
  totalSSEStreams: number;
  avgDuration: number;
}

interface ArtifactSummary {
  id: string;
  name: string;
  duration: number;
  toolCalls: number;
  hasSSE: boolean;
  hasError: boolean;
  createdAt: string;
  filePath: string;
}

export function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    totalRuns: 0,
    mcpSessions: 0,
    avgARSScore: 0,
    totalToolCalls: 0,
    totalSSEStreams: 0,
    avgDuration: 0,
  });
  const [recentArtifacts, setRecentArtifacts] = useState<ArtifactSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const artifactFiles = [
        'basic-agent-run.kurral',
        'mcp-sse-capture.kurral',
        'replay-with-ars.kurral',
        'replay-detailed-ars.kurral',
        'complex-sse-multi-stream.kurral',
        'sse-error-handling.kurral',
        'fast-sse-stream.kurral',
      ];

      const artifacts: KurralArtifact[] = [];
      for (const file of artifactFiles) {
        const response = await fetch(`/mock-artifacts/${file}`);
        const data = await response.json();
        artifacts.push(data);
      }

      // Calculate stats
      const totalRuns = artifacts.length;
      const mcpSessions = new Set(artifacts.map(a => a.mcp_session_id).filter(Boolean)).size;

      const arsScores = artifacts
        .filter(a => a.replay_info?.ars_score !== undefined)
        .map(a => a.replay_info!.ars_score);
      const avgARSScore = arsScores.length > 0
        ? arsScores.reduce((sum, score) => sum + score, 0) / arsScores.length
        : 0;

      const totalToolCalls = artifacts.reduce((sum, a) => {
        return sum + a.tool_calls.length + (a.mcp_tool_calls?.length || 0);
      }, 0);

      const totalSSEStreams = artifacts.reduce((sum, a) => {
        return sum + (a.mcp_tool_calls?.filter(call => call.was_sse).length || 0);
      }, 0);

      const avgDuration = artifacts.reduce((sum, a) => sum + a.duration_ms, 0) / artifacts.length;

      setStats({
        totalRuns,
        mcpSessions,
        avgARSScore,
        totalToolCalls,
        totalSSEStreams,
        avgDuration,
      });

      // Build recent artifacts summary
      const summaries: ArtifactSummary[] = artifacts.map((artifact, idx) => ({
        id: artifact.kurral_id,
        name: artifact.run_id,
        duration: artifact.duration_ms,
        toolCalls: artifact.tool_calls.length + (artifact.mcp_tool_calls?.length || 0),
        hasSSE: (artifact.mcp_tool_calls?.some(call => call.was_sse)) || false,
        hasError: (artifact.mcp_tool_calls?.some(call => call.error)) || false,
        createdAt: artifact.created_at,
        filePath: artifactFiles[idx],
      }));

      // Sort by created_at descending
      summaries.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

      setRecentArtifacts(summaries);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-12 h-12 text-kurral-blue mx-auto animate-spin" />
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <img
              src="/kurral-logo.png"
              alt="Kurral Logo"
              className="w-12 h-12 object-contain"
            />
            <div>
              <h1 className="text-4xl font-bold text-gray-900">Kurral Dashboard</h1>
              <p className="text-gray-600">Monitor your AI agent execution traces and MCP sessions</p>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {/* Total Runs */}
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100 hover:shadow-xl transition-shadow">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-kurral-blue to-kurral-cyan rounded-lg flex items-center justify-center">
                <Activity className="w-6 h-6 text-white" />
              </div>
              <TrendingUp className="w-5 h-5 text-green-500" />
            </div>
            <div className="text-3xl font-bold text-gray-900 mb-1">{stats.totalRuns}</div>
            <div className="text-sm text-gray-600 font-medium">Total Artifact Runs</div>
          </div>

          {/* MCP Sessions */}
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100 hover:shadow-xl transition-shadow">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-kurral-cyan to-kurral-cyan-light rounded-lg flex items-center justify-center">
                <Zap className="w-6 h-6 text-white" />
              </div>
              <Server className="w-5 h-5 text-kurral-cyan" />
            </div>
            <div className="text-3xl font-bold text-gray-900 mb-1">{stats.mcpSessions}</div>
            <div className="text-sm text-gray-600 font-medium">MCP Sessions</div>
          </div>

          {/* Average ARS Score */}
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100 hover:shadow-xl transition-shadow">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-kurral-purple to-kurral-purple-bright rounded-lg flex items-center justify-center">
                <Award className="w-6 h-6 text-white" />
              </div>
              {stats.avgARSScore > 0.8 && <CheckCircle className="w-5 h-5 text-green-500" />}
            </div>
            <div className="text-3xl font-bold text-gray-900 mb-1">
              {stats.avgARSScore > 0 ? stats.avgARSScore.toFixed(2) : 'N/A'}
            </div>
            <div className="text-sm text-gray-600 font-medium">Average ARS Score</div>
          </div>

          {/* Total Tool Calls */}
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100 hover:shadow-xl transition-shadow">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-kurral-purple-mid to-kurral-purple-light rounded-lg flex items-center justify-center">
                <Wrench className="w-6 h-6 text-white" />
              </div>
            </div>
            <div className="text-3xl font-bold text-gray-900 mb-1">{stats.totalToolCalls}</div>
            <div className="text-sm text-gray-600 font-medium">Total Tool Calls</div>
          </div>

          {/* SSE Streams */}
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100 hover:shadow-xl transition-shadow">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-cyan-500 to-blue-500 rounded-lg flex items-center justify-center">
                <Activity className="w-6 h-6 text-white" />
              </div>
            </div>
            <div className="text-3xl font-bold text-gray-900 mb-1">{stats.totalSSEStreams}</div>
            <div className="text-sm text-gray-600 font-medium">SSE Streams</div>
          </div>

          {/* Average Duration */}
          <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100 hover:shadow-xl transition-shadow">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-gray-600 to-gray-800 rounded-lg flex items-center justify-center">
                <Clock className="w-6 h-6 text-white" />
              </div>
            </div>
            <div className="text-3xl font-bold text-gray-900 mb-1">
              {(stats.avgDuration / 1000).toFixed(1)}s
            </div>
            <div className="text-sm text-gray-600 font-medium">Average Duration</div>
          </div>
        </div>

        {/* Recent Artifacts */}
        <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden">
          <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white">
            <div className="flex items-center gap-3">
              <FileText className="w-6 h-6 text-kurral-blue" />
              <h2 className="text-2xl font-bold text-gray-900">Recent Artifacts</h2>
            </div>
            <p className="text-sm text-gray-600 mt-1">Click on any artifact to view detailed trace</p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Run ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Duration
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Tool Calls
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Features
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {recentArtifacts.map((artifact) => (
                  <tr key={artifact.id} className="hover:bg-blue-50/50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-900">{artifact.name}</div>
                      <div className="text-xs text-gray-500 font-mono">{artifact.id.slice(0, 20)}...</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-gray-400" />
                        <span className="text-sm font-semibold text-gray-700">
                          {artifact.duration > 1000
                            ? `${(artifact.duration / 1000).toFixed(1)}s`
                            : `${artifact.duration}ms`
                          }
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2.5 py-1 bg-gray-100 text-gray-700 rounded-full text-sm font-semibold">
                        {artifact.toolCalls}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-2">
                        {artifact.hasSSE && (
                          <span className="px-2 py-1 bg-cyan-100 text-cyan-700 rounded text-xs font-medium">
                            SSE
                          </span>
                        )}
                        {artifact.hasError && (
                          <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs font-medium flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" />
                            Error
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-gray-600">
                        {new Date(artifact.createdAt).toLocaleDateString()}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <Link
                        to={`/trace?artifact=${artifact.filePath}`}
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-kurral-blue text-white rounded-lg hover:bg-kurral-blue/90 transition-colors text-sm font-medium"
                      >
                        View Trace
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* MCP Proxy Status */}
        <div className="mt-8 bg-white rounded-xl shadow-lg border border-gray-100 p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center">
                  <Server className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-900">MCP Proxy Status</h3>
              </div>
              <p className="text-sm text-gray-600 ml-13">Monitor your Model Context Protocol proxy server</p>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-green-50 border border-green-200 rounded-lg">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-sm font-semibold text-green-700">Ready (Mock)</span>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <div className="text-xs text-gray-600 mb-1">Endpoint</div>
              <div className="text-sm font-mono text-gray-900">http://localhost:8000</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <div className="text-xs text-gray-600 mb-1">Active Sessions</div>
              <div className="text-sm font-semibold text-gray-900">{stats.mcpSessions}</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <div className="text-xs text-gray-600 mb-1">Total Streams</div>
              <div className="text-sm font-semibold text-gray-900">{stats.totalSSEStreams}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
