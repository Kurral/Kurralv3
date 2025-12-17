/**
 * Kurral to Trace Adapter
 * Converts .kurral artifacts to trace visualization format
 */

import type { KurralArtifact, KurralToolCall, KurralMCPCall } from '../types/kurral';
import type { TraceSpan, TraceRecord, Badge, SpanStatus } from '../types/trace';

/**
 * Convert a Kurral artifact to trace format
 */
export function convertKurralToTrace(artifact: KurralArtifact): {
  traceRecord: TraceRecord;
  spans: TraceSpan[];
} {
  const spans: TraceSpan[] = [];

  // Convert standard tool calls
  for (const call of artifact.tool_calls) {
    spans.push(convertToolCallToSpan(call));
  }

  // Convert MCP tool calls (if present)
  if (artifact.mcp_tool_calls) {
    for (const mcpCall of artifact.mcp_tool_calls) {
      spans.push(convertMCPCallToSpan(mcpCall));
    }
  }

  // Build TraceRecord (trace-level metadata)
  const traceRecord: TraceRecord = {
    id: artifact.kurral_id,
    name: artifact.run_id,
    spansCount: spans.length,
    durationMs: artifact.duration_ms,
    agentDescription: `${artifact.llm_config.provider}/${artifact.llm_config.model_name}`,
    createdAt: artifact.created_at,
  };

  return { traceRecord, spans };
}

/**
 * Convert a standard tool call to a trace span
 */
function convertToolCallToSpan(call: KurralToolCall): TraceSpan {
  const status: SpanStatus = call.error_flag ? 'error' : 'success';

  return {
    id: call.id,
    name: call.tool_name,
    parentId: null, // Kurral uses flat list - no hierarchy in MVP
    startTime: new Date(call.start_time).getTime(),
    endTime: new Date(call.end_time).getTime(),
    category: 'tool',
    status,
    attributes: {
      'kurral.cache_key': call.cache_key,
      'kurral.stubbed': call.stubbed_in_replay,
      'kurral.effect_type': call.effect_type,
      'kurral.input_hash': call.input_hash,
      'kurral.output_hash': call.output_hash,
      'kurral.latency_ms': call.latency_ms,
    },
    input: call.input,
    output: call.output,
  };
}

/**
 * Convert an MCP call to a trace span
 */
function convertMCPCallToSpan(mcpCall: KurralMCPCall): TraceSpan {
  const status: SpanStatus = mcpCall.error ? 'error' : 'success';

  return {
    id: mcpCall.id,
    name: `MCP: ${mcpCall.tool_name || mcpCall.method}`,
    parentId: null,
    startTime: new Date(mcpCall.timestamp).getTime(),
    endTime: new Date(mcpCall.timestamp).getTime() + mcpCall.duration_ms,
    category: 'mcp' as any, // Custom category for MCP
    status,
    attributes: {
      'mcp.server': mcpCall.server,
      'mcp.method': mcpCall.method,
      'mcp.was_sse': mcpCall.was_sse,
      'mcp.event_count': mcpCall.events?.length || 0,
      'mcp.time_to_first_event_ms': mcpCall.metrics?.time_to_first_event_ms,
      'mcp.events_per_second': mcpCall.metrics?.events_per_second,
    },
    input: mcpCall.arguments,
    output: mcpCall.result,
    error: mcpCall.error,
  };
}

/**
 * Build badges for trace display
 */
export function buildArtifactBadges(artifact: KurralArtifact): Badge[] {
  const badges: Badge[] = [];

  // Model badge
  badges.push({
    label: artifact.llm_config.model_name,
    variant: 'default',
  });

  // ARS score badge (if replay)
  if (artifact.ars_score !== undefined) {
    const variant =
      artifact.ars_score >= 0.9
        ? 'success'
        : artifact.ars_score >= 0.7
        ? 'warning'
        : 'error';
    badges.push({
      label: `ARS: ${artifact.ars_score.toFixed(2)}`,
      variant,
    });
  }

  // Replay mode badge
  if (artifact.replay_mode) {
    badges.push({
      label: `Replay ${artifact.replay_mode.toUpperCase()}`,
      variant: 'info',
    });
  }

  // MCP badge
  if (artifact.mcp_tool_calls?.length) {
    badges.push({
      label: `MCP: ${artifact.mcp_tool_calls.length} calls`,
      variant: 'info',
    });
  }

  // Determinism badge
  if (artifact.deterministic) {
    badges.push({
      label: 'Deterministic',
      variant: 'success',
    });
  }

  return badges;
}

/**
 * Extract key metrics from artifact
 */
export function extractMetrics(artifact: KurralArtifact) {
  const totalCalls = artifact.tool_calls.length + (artifact.mcp_tool_calls?.length || 0);
  const mcpSSECalls = artifact.mcp_tool_calls?.filter((c) => c.was_sse).length || 0;
  const avgLatency =
    artifact.tool_calls.reduce((sum, call) => sum + call.latency_ms, 0) /
    artifact.tool_calls.length;

  return {
    totalCalls,
    mcpCalls: artifact.mcp_tool_calls?.length || 0,
    mcpSSECalls,
    avgLatency: Math.round(avgLatency),
    duration: artifact.duration_ms,
    model: `${artifact.llm_config.provider}/${artifact.llm_config.model_name}`,
  };
}
