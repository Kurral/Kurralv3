import React, { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, Zap, Activity, CheckCircle, XCircle, Clock } from 'lucide-react';
import type { MCPEvent } from '../../types/kurral';
import { JsonViewer } from '../common/JsonViewer';

interface SSEEventTimelineProps {
  events: MCPEvent[];
  totalDurationMs: number;
  timeToFirstEventMs?: number;
  eventsPerSecond?: number;
}

export function SSEEventTimeline({
  events,
  totalDurationMs,
  timeToFirstEventMs,
  eventsPerSecond,
}: SSEEventTimelineProps) {
  const [expandedEvents, setExpandedEvents] = useState<Set<number>>(new Set());

  const toggleEvent = (index: number) => {
    const newExpanded = new Set(expandedEvents);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedEvents(newExpanded);
  };

  // Calculate relative timestamps
  const eventsWithTimings = useMemo(() => {
    if (events.length === 0) return [];

    const startTime = new Date(events[0].timestamp).getTime();
    return events.map((event, index) => {
      const eventTime = new Date(event.timestamp).getTime();
      const relativeMs = eventTime - startTime;
      const percentOfTotal = (relativeMs / totalDurationMs) * 100;

      return {
        ...event,
        index,
        relativeMs,
        percentOfTotal,
      };
    });
  }, [events, totalDurationMs]);

  // Event type styling
  const getEventStyle = (eventType: string) => {
    const styles = {
      start: {
        color: 'bg-green-500',
        icon: <Zap className="w-4 h-4 text-white" />,
        label: 'START',
        bgLight: 'bg-green-50',
        borderLight: 'border-green-200',
        textLight: 'text-green-700',
      },
      progress: {
        color: 'bg-blue-500',
        icon: <Activity className="w-4 h-4 text-white" />,
        label: 'PROGRESS',
        bgLight: 'bg-blue-50',
        borderLight: 'border-blue-200',
        textLight: 'text-blue-700',
      },
      complete: {
        color: 'bg-green-600',
        icon: <CheckCircle className="w-4 h-4 text-white" />,
        label: 'COMPLETE',
        bgLight: 'bg-green-50',
        borderLight: 'border-green-200',
        textLight: 'text-green-700',
      },
      error: {
        color: 'bg-red-500',
        icon: <XCircle className="w-4 h-4 text-white" />,
        label: 'ERROR',
        bgLight: 'bg-red-50',
        borderLight: 'border-red-200',
        textLight: 'text-red-700',
      },
      message: {
        color: 'bg-gray-500',
        icon: <Activity className="w-4 h-4 text-white" />,
        label: 'MESSAGE',
        bgLight: 'bg-gray-50',
        borderLight: 'border-gray-200',
        textLight: 'text-gray-700',
      },
    };

    return styles[eventType as keyof typeof styles] || styles.message;
  };

  return (
    <div className="bg-gradient-to-br from-cyan-50 to-blue-50 rounded-lg border border-cyan-200 p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 bg-gradient-to-br from-kurral-cyan to-kurral-cyan-light rounded-lg flex items-center justify-center">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <h4 className="text-lg font-bold text-gray-900">SSE Stream Events</h4>
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-white rounded-lg p-3 border border-cyan-200">
            <div className="text-xs text-gray-600 mb-1">Duration</div>
            <div className="text-lg font-bold text-gray-900">{totalDurationMs}ms</div>
          </div>
          <div className="bg-white rounded-lg p-3 border border-cyan-200">
            <div className="text-xs text-gray-600 mb-1">Events</div>
            <div className="text-lg font-bold text-gray-900">{events.length}</div>
          </div>
          {timeToFirstEventMs !== undefined && (
            <div className="bg-white rounded-lg p-3 border border-cyan-200">
              <div className="text-xs text-gray-600 mb-1">Time to First</div>
              <div className="text-lg font-bold text-gray-900">{timeToFirstEventMs}ms</div>
            </div>
          )}
          {eventsPerSecond !== undefined && (
            <div className="bg-white rounded-lg p-3 border border-cyan-200">
              <div className="text-xs text-gray-600 mb-1">Events/sec</div>
              <div className="text-lg font-bold text-gray-900">{eventsPerSecond.toFixed(1)}</div>
            </div>
          )}
        </div>
      </div>

      {/* Timeline */}
      <div className="space-y-3">
        {eventsWithTimings.map((event, idx) => {
          const isExpanded = expandedEvents.has(idx);
          const style = getEventStyle(event.event_type);
          const isFirst = idx === 0;
          const isLast = idx === eventsWithTimings.length - 1;

          return (
            <div key={idx} className="relative">
              {/* Timeline connector */}
              {!isLast && (
                <div className="absolute left-[19px] top-[40px] w-0.5 h-full bg-gradient-to-b from-cyan-300 to-transparent z-0" />
              )}

              {/* Event Card */}
              <div className={`relative z-10 bg-white rounded-lg border-2 ${style.borderLight} overflow-hidden transition-all ${
                isExpanded ? 'shadow-lg' : 'shadow-sm hover:shadow-md'
              }`}>
                <div className="flex items-start gap-4 p-4">
                  {/* Timeline Marker */}
                  <div className={`w-10 h-10 ${style.color} rounded-full flex items-center justify-center flex-shrink-0 shadow-md`}>
                    {style.icon}
                  </div>

                  {/* Event Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className={`px-2 py-0.5 ${style.bgLight} ${style.textLight} rounded text-xs font-bold uppercase tracking-wide`}>
                          {style.label}
                        </span>
                        <span className="text-xs text-gray-500 font-mono">
                          {event.relativeMs}ms
                        </span>
                        {event.percentOfTotal > 0 && (
                          <span className="text-xs text-gray-400">
                            ({event.percentOfTotal.toFixed(1)}% of stream)
                          </span>
                        )}
                      </div>

                      <button
                        onClick={() => toggleEvent(idx)}
                        className="text-gray-500 hover:text-gray-700 transition-colors ml-2"
                      >
                        {isExpanded ? (
                          <ChevronDown className="w-5 h-5" />
                        ) : (
                          <ChevronRight className="w-5 h-5" />
                        )}
                      </button>
                    </div>

                    {/* Event Preview */}
                    {!isExpanded && (
                      <div className="text-sm text-gray-700 truncate">
                        {typeof event.data === 'object' ? (
                          <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                            {JSON.stringify(event.data).slice(0, 100)}...
                          </span>
                        ) : (
                          event.data
                        )}
                      </div>
                    )}

                    {/* Expanded Event Data */}
                    {isExpanded && (
                      <div className="mt-3">
                        <JsonViewer
                          data={event.data}
                          title="Event Data"
                          maxHeight="300px"
                        />
                      </div>
                    )}
                  </div>
                </div>

                {/* Progress indicator for progress events */}
                {event.event_type === 'progress' && typeof event.data === 'object' && 'progress' in event.data && (
                  <div className="px-4 pb-4">
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-300"
                        style={{ width: `${(event.data.progress as number) * 100}%` }}
                      />
                    </div>
                    <div className="text-xs text-gray-600 mt-1 text-right">
                      {((event.data.progress as number) * 100).toFixed(0)}% complete
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Stream Summary */}
      {events.length > 0 && (
        <div className="mt-6 p-4 bg-white rounded-lg border border-cyan-200">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-gray-600" />
            <span className="text-sm font-semibold text-gray-900">Stream Summary</span>
          </div>
          <p className="text-sm text-gray-700">
            Streamed <span className="font-bold text-cyan-700">{events.length} events</span> over{' '}
            <span className="font-bold text-cyan-700">{totalDurationMs}ms</span>
            {timeToFirstEventMs !== undefined && (
              <>
                {' '}with first event at <span className="font-bold text-cyan-700">{timeToFirstEventMs}ms</span>
              </>
            )}
          </p>
        </div>
      )}
    </div>
  );
}
