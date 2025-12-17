import React from 'react';
import { Award, CheckCircle, AlertTriangle, XCircle, Info, TrendingUp, Copy } from 'lucide-react';
import type { ReplayInfo, PerToolARS } from '../../types/kurral';
import { JsonViewer } from '../common/JsonViewer';

interface ReplayARSBreakdownProps {
  replayInfo: ReplayInfo;
}

export function ReplayARSBreakdown({ replayInfo }: ReplayARSBreakdownProps) {
  const getARSColor = (score: number) => {
    if (score >= 0.9) return 'text-green-600';
    if (score >= 0.7) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getARSBgColor = (score: number) => {
    if (score >= 0.9) return 'bg-green-50 border-green-200';
    if (score >= 0.7) return 'bg-yellow-50 border-yellow-200';
    return 'bg-red-50 border-red-200';
  };

  const getMatchIcon = (status: PerToolARS['match_status']) => {
    switch (status) {
      case 'exact':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'near_match':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      case 'mismatch':
        return <XCircle className="w-5 h-5 text-red-500" />;
    }
  };

  const getMatchLabel = (status: PerToolARS['match_status']) => {
    switch (status) {
      case 'exact':
        return 'Exact Match';
      case 'near_match':
        return 'Near Match';
      case 'mismatch':
        return 'Mismatch';
    }
  };

  const getMatchBadgeColor = (status: PerToolARS['match_status']) => {
    switch (status) {
      case 'exact':
        return 'bg-green-100 text-green-700 border-green-300';
      case 'near_match':
        return 'bg-yellow-100 text-yellow-700 border-yellow-300';
      case 'mismatch':
        return 'bg-red-100 text-red-700 border-red-300';
    }
  };

  return (
    <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-xl border-2 border-purple-200 p-6 shadow-lg">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-12 h-12 bg-gradient-to-br from-kurral-purple to-kurral-purple-bright rounded-lg flex items-center justify-center shadow-md">
            <Award className="w-7 h-7 text-white" />
          </div>
          <div>
            <h3 className="text-2xl font-bold text-gray-900">Replay Analysis</h3>
            <p className="text-sm text-gray-600">Artifact Reproducibility Score (ARS) Breakdown</p>
          </div>
        </div>
      </div>

      {/* Overall Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {/* ARS Score */}
        <div className={`rounded-lg p-4 border-2 ${getARSBgColor(replayInfo.ars_score)}`}>
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className={`w-5 h-5 ${getARSColor(replayInfo.ars_score)}`} />
            <div className="text-xs font-semibold text-gray-700 uppercase">ARS Score</div>
          </div>
          <div className={`text-3xl font-bold ${getARSColor(replayInfo.ars_score)}`}>
            {(replayInfo.ars_score * 100).toFixed(1)}%
          </div>
        </div>

        {/* Determinism Score */}
        <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-5 h-5 text-blue-600" />
            <div className="text-xs font-semibold text-gray-700 uppercase">Determinism</div>
          </div>
          <div className="text-3xl font-bold text-blue-600">
            {(replayInfo.determinism_score * 100).toFixed(0)}%
          </div>
        </div>

        {/* Stubbed Calls */}
        <div className="bg-cyan-50 border-2 border-cyan-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Copy className="w-5 h-5 text-cyan-600" />
            <div className="text-xs font-semibold text-gray-700 uppercase">Stubbed</div>
          </div>
          <div className="text-3xl font-bold text-cyan-600">
            {replayInfo.stubbed_calls}/{replayInfo.total_tool_calls}
          </div>
        </div>

        {/* Live Calls */}
        <div className="bg-purple-50 border-2 border-purple-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Info className="w-5 h-5 text-purple-600" />
            <div className="text-xs font-semibold text-gray-700 uppercase">Live</div>
          </div>
          <div className="text-3xl font-bold text-purple-600">
            {replayInfo.live_calls}/{replayInfo.total_tool_calls}
          </div>
        </div>
      </div>

      {/* Comparison Notes */}
      {replayInfo.comparison_notes && (
        <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-semibold text-blue-900 mb-1">Analysis Notes</h4>
              <p className="text-sm text-blue-800">{replayInfo.comparison_notes}</p>
            </div>
          </div>
        </div>
      )}

      {/* Per-Tool Breakdown */}
      {replayInfo.per_tool_ars && replayInfo.per_tool_ars.length > 0 && (
        <div>
          <h4 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Award className="w-5 h-5 text-purple-600" />
            Per-Tool ARS Breakdown
          </h4>

          <div className="space-y-3">
            {replayInfo.per_tool_ars.map((toolARS, idx) => (
              <div
                key={idx}
                className="bg-white rounded-lg border-2 border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
              >
                <div className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3 flex-1">
                      {getMatchIcon(toolARS.match_status)}
                      <div className="flex-1">
                        <div className="font-semibold text-gray-900 text-base">
                          {toolARS.tool_name}
                        </div>
                        <div className="text-xs text-gray-500 font-mono">{toolARS.tool_id}</div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-semibold border ${getMatchBadgeColor(
                          toolARS.match_status
                        )}`}
                      >
                        {getMatchLabel(toolARS.match_status)}
                      </span>
                      <div className={`text-2xl font-bold ${getARSColor(toolARS.ars_score)}`}>
                        {(toolARS.ars_score * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="mb-3">
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all ${
                          toolARS.ars_score >= 0.9
                            ? 'bg-green-500'
                            : toolARS.ars_score >= 0.7
                            ? 'bg-yellow-500'
                            : 'bg-red-500'
                        }`}
                        style={{ width: `${toolARS.ars_score * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* Output Diff */}
                  {toolARS.output_diff && (
                    <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3">
                      <div className="flex items-start gap-2 mb-2">
                        <XCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                        <div className="flex-1">
                          <h5 className="text-sm font-semibold text-red-900 mb-1">
                            Output Difference Detected
                          </h5>
                          <div className="text-xs text-red-800 mb-2">
                            <strong>Field:</strong> {toolARS.output_diff.field}
                          </div>
                          <div className="grid grid-cols-2 gap-3 text-xs">
                            <div className="bg-white border border-red-300 rounded p-2">
                              <div className="text-gray-600 font-semibold mb-1">Original</div>
                              <div className="font-mono text-gray-900">
                                {typeof toolARS.output_diff.original === 'object'
                                  ? JSON.stringify(toolARS.output_diff.original)
                                  : toolARS.output_diff.original}
                              </div>
                            </div>
                            <div className="bg-white border border-red-300 rounded p-2">
                              <div className="text-gray-600 font-semibold mb-1">Replay</div>
                              <div className="font-mono text-gray-900">
                                {typeof toolARS.output_diff.replay === 'object'
                                  ? JSON.stringify(toolARS.output_diff.replay)
                                  : toolARS.output_diff.replay}
                              </div>
                            </div>
                          </div>
                          <div className="mt-2 text-xs text-red-700 italic">
                            <strong>Analysis:</strong> {toolARS.output_diff.difference}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Exact Match Indicator */}
                  {!toolARS.output_diff && toolARS.match_status === 'exact' && (
                    <div className="mt-3 bg-green-50 border border-green-200 rounded-lg p-2">
                      <div className="flex items-center gap-2 text-sm text-green-800">
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        <span className="font-medium">Output matched exactly between original and replay</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
