/**
 * Agent Prism Compatible Trace Types
 * Simplified version for our MVP - we'll build our own trace viewer
 */

export type SpanCategory = 'llm' | 'tool' | 'agent' | 'chain' | 'retriever' | 'mcp';
export type SpanStatus = 'success' | 'error' | 'pending';

export interface TraceSpan {
  id: string;
  name: string;
  parentId: string | null;
  startTime: number; // milliseconds timestamp
  endTime: number; // milliseconds timestamp
  category: SpanCategory;
  status: SpanStatus;
  attributes: Record<string, any>;
  input?: any;
  output?: any;
  error?: any;
}

export interface TraceRecord {
  id: string;
  name: string;
  spansCount: number;
  durationMs: number;
  agentDescription?: string;
  createdAt?: string;
}

export interface Badge {
  label: string;
  variant: 'default' | 'success' | 'warning' | 'error' | 'info';
}
