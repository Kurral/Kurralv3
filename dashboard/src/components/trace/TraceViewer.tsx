import React, { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, Clock, CheckCircle2, XCircle, AlertCircle, Waves } from 'lucide-react';
import type { TraceRecord, TraceSpan } from '../../types/trace';
import type { KurralArtifact } from '../../types/kurral';
import { buildArtifactBadges } from '../../adapters/kurralAdapter';
import { JsonViewer } from '../common/JsonViewer';
import { SSEEventTimeline } from '../mcp/SSEEventTimeline';
import { ReplayARSBreakdown } from '../replay/ReplayARSBreakdown';

interface TraceViewerProps {
  artifact: KurralArtifact;
  traceRecord: TraceRecord;
  spans: TraceSpan[];
}

export function TraceViewer({ artifact, traceRecord, spans }: TraceViewerProps) {
  const [expandedSpans, setExpandedSpans] = useState<Set<string>>(new Set());
  const badges = buildArtifactBadges(artifact);

  const toggleSpan = (spanId: string) => {
    const newExpanded = new Set(expandedSpans);
    if (newExpanded.has(spanId)) {
      newExpanded.delete(spanId);
    } else {
      newExpanded.add(spanId);
    }
    setExpandedSpans(newExpanded);
  };

  // Helper to find MCP events for a span
  const getMCPEventsForSpan = (spanId: string) => {
    if (!artifact.mcp_tool_calls) return null;

    const mcpCall = artifact.mcp_tool_calls.find(call => call.id === spanId);
    if (!mcpCall || !mcpCall.was_sse || !mcpCall.events || mcpCall.events.length === 0) {
      return null;
    }

    return {
      events: mcpCall.events,
      metrics: mcpCall.metrics,
    };
  };

  // Calculate timeline positions and time markers
  const { minTime, maxTime, timeRange, timeMarkers } = useMemo(() => {
    const min = Math.min(...spans.map(s => s.startTime));
    const max = Math.max(...spans.map(s => s.endTime));
    const range = max - min || 1;

    // Generate time markers (every 20% of timeline)
    const markers = [];
    for (let i = 0; i <= 5; i++) {
      const position = (i / 5) * 100;
      const time = min + (range * i / 5);
      const relativeMs = Math.round(time - min);
      markers.push({ position, time: relativeMs });
    }

    return { minTime: min, maxTime: max, timeRange: range, timeMarkers: markers };
  }, [spans]);

  const getSpanPosition = (span: TraceSpan) => {
    const left = ((span.startTime - minTime) / timeRange) * 100;
    const width = ((span.endTime - span.startTime) / timeRange) * 100;
    return { left: `${left}%`, width: `${Math.max(width, 0.5)}%` };
  };

  const getCategoryColor = (category: TraceSpan['category']) => {
    const colors = {
      llm: 'bg-kurral-cyan',
      tool: 'bg-kurral-purple-bright',
      agent: 'bg-kurral-blue',
      chain: 'bg-kurral-purple-mid',
      retriever: 'bg-kurral-purple-light',
      mcp: 'bg-gradient-to-r from-kurral-cyan to-kurral-cyan-light',
    };
    return colors[category] || 'bg-gray-500';
  };

  const getCategoryIcon = (status: TraceSpan['status']) => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-500 flex-shrink-0" />;
      case 'pending':
        return <AlertCircle className="w-5 h-5 text-yellow-500 flex-shrink-0" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400 flex-shrink-0" />;
    }
  };

  const isReplay = artifact.replay_mode !== undefined;

  return (
    <div className="space-y-6">
      {/* Replay ARS Breakdown (if applicable) */}
      {isReplay && artifact.replay_info && (
        <ReplayARSBreakdown replayInfo={artifact.replay_info} />
      )}

      {/* Trace Header */}
      <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h2 className="text-3xl font-bold text-gray-900 mb-2">{traceRecord.name}</h2>
            <p className="text-sm text-gray-500 font-mono">ID: {traceRecord.id}</p>
            {traceRecord.agentDescription && (
              <p className="text-sm text-gray-600 mt-1 font-medium">{traceRecord.agentDescription}</p>
            )}
          </div>

          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-3 text-sm">
              <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 rounded-lg">
                <Clock className="w-4 h-4 text-gray-600" />
                <span className="font-semibold text-gray-900">{traceRecord.durationMs}ms</span>
              </div>
              <div className="px-3 py-1.5 bg-kurral-blue/10 text-kurral-blue rounded-lg font-semibold">
                {traceRecord.spansCount} spans
              </div>
            </div>
          </div>
        </div>

        {/* Badges */}
        {badges.length > 0 && (
          <div className="flex gap-2 flex-wrap">
            {badges.map((badge, idx) => (
              <span
                key={idx}
                className={`kurral-badge ${
                  badge.variant === 'success'
                    ? 'kurral-badge-success'
                    : badge.variant === 'warning'
                    ? 'kurral-badge-warning'
                    : badge.variant === 'error'
                    ? 'kurral-badge-error'
                    : 'kurral-badge-info'
                }`}
              >
                {badge.label}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Timeline Visualization */}
      <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden">
        <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white">
          <h3 className="text-lg font-semibold text-gray-900">Execution Timeline</h3>
          <p className="text-sm text-gray-600 mt-1">
            Hover over spans for details, click to expand full information
          </p>
        </div>

        {/* Time Markers */}
        <div className="px-6 py-3 bg-gray-50 border-b border-gray-200">
          <div className="relative h-6">
            {timeMarkers.map((marker, idx) => (
              <div
                key={idx}
                className="absolute top-0 flex flex-col items-center"
                style={{ left: `${marker.position}%`, transform: 'translateX(-50%)' }}
              >
                <div className="w-px h-2 bg-gray-300" />
                <span className="text-xs text-gray-500 mt-1 font-mono">{marker.time}ms</span>
              </div>
            ))}
          </div>
        </div>

        {/* Spans */}
        <div className="divide-y divide-gray-100">
          {spans.map((span, index) => {
            const isExpanded = expandedSpans.has(span.id);
            const duration = span.endTime - span.startTime;
            const position = getSpanPosition(span);
            const relativeStart = Math.round(span.startTime - minTime);
            const mcpEventData = getMCPEventsForSpan(span.id);
            const hasSSE = mcpEventData !== null;

            return (
              <div
                key={span.id}
                className={`transition-all ${
                  isExpanded ? 'bg-blue-50/30' : 'hover:bg-gray-50'
                }`}
              >
                {/* Span Header */}
                <div className="p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <button
                      onClick={() => toggleSpan(span.id)}
                      className="text-gray-500 hover:text-gray-700 transition-colors"
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-5 h-5" />
                      ) : (
                        <ChevronRight className="w-5 h-5" />
                      )}
                    </button>

                    {getCategoryIcon(span.status)}

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="font-semibold text-gray-900 text-base">
                          {span.name}
                        </span>
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2.5 py-0.5 text-xs font-medium rounded-full ${getCategoryColor(
                              span.category
                            )} text-white shadow-sm`}
                          >
                            {span.category}
                          </span>
                          {hasSSE && (
                            <span className="px-2.5 py-0.5 text-xs font-medium rounded-full bg-cyan-100 text-cyan-700 flex items-center gap-1">
                              <Waves className="w-3 h-3" />
                              SSE Stream
                            </span>
                          )}
                          <span className="text-xs text-gray-500 font-mono">
                            {relativeStart}ms → {relativeStart + duration}ms
                          </span>
                          <span className="text-xs font-semibold text-gray-700 bg-gray-100 px-2 py-0.5 rounded">
                            {duration}ms
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Visual Timeline Bar */}
                  <div className="ml-11">
                    <div className="relative h-3 bg-gray-100 rounded-full overflow-hidden shadow-inner">
                      {/* Background grid */}
                      {timeMarkers.map((marker, idx) => (
                        <div
                          key={idx}
                          className="absolute top-0 bottom-0 w-px bg-gray-200"
                          style={{ left: `${marker.position}%` }}
                        />
                      ))}
                      {/* Span bar */}
                      <div
                        className={`absolute h-full ${getCategoryColor(span.category)} shadow-md transition-all hover:shadow-lg`}
                        style={position}
                        title={`${span.name}: ${duration}ms`}
                      />
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {isExpanded && (
                    <div className="ml-11 mt-4 space-y-4">
                      {/* SSE Event Timeline (if applicable) */}
                      {hasSSE && mcpEventData && (
                        <SSEEventTimeline
                          events={mcpEventData.events}
                          totalDurationMs={duration}
                          timeToFirstEventMs={mcpEventData.metrics?.time_to_first_event_ms}
                          eventsPerSecond={mcpEventData.metrics?.events_per_second}
                        />
                      )}

                      {/* Regular Input/Output (for non-SSE or alongside SSE) */}
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        {/* Input */}
                        {span.input && (
                          <JsonViewer data={span.input} title="Input" maxHeight="400px" />
                        )}

                        {/* Output (only if not SSE or as additional data) */}
                        {span.output && !hasSSE && (
                          <JsonViewer data={span.output} title="Output" maxHeight="400px" />
                        )}

                        {/* Final Result for SSE */}
                        {span.output && hasSSE && (
                          <JsonViewer data={span.output} title="Final Result" maxHeight="400px" />
                        )}
                      </div>

                      {/* Error */}
                      {span.error && (
                        <JsonViewer data={span.error} title="Error" maxHeight="300px" />
                      )}

                      {/* Attributes */}
                      {Object.keys(span.attributes).length > 0 && (
                        <div>
                          <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
                            Attributes
                          </h4>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                            {Object.entries(span.attributes).map(([key, value]) => (
                              <div
                                key={key}
                                className="bg-gray-50 border border-gray-200 rounded-lg p-3"
                              >
                                <div className="text-xs text-gray-600 mb-1">{key}</div>
                                <div className="text-sm text-gray-900 font-mono break-all">
                                  {typeof value === 'boolean'
                                    ? value.toString()
                                    : typeof value === 'object'
                                    ? JSON.stringify(value)
                                    : value}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
