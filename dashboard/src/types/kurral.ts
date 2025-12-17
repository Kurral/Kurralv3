/**
 * Kurral Artifact Types
 * Based on actual .kurral file format from PRD
 */

export interface KurralToolCall {
  id: string;
  tool_name: string;
  start_time: string; // ISO timestamp
  end_time: string; // ISO timestamp
  latency_ms: number;
  timestamp: string;
  input: Record<string, any>;
  input_hash: string;
  output: Record<string, any>;
  output_hash: string;
  type: string; // "tool"
  effect_type: string; // "other", "side_effect"
  status: string; // "ok", "error"
  error_flag: boolean;
  cache_key: string;
  stubbed_in_replay: boolean;
  metadata: Record<string, any>;
}

export interface MCPEvent {
  event_type: string;
  data: any;
  timestamp: string;
}

export interface MCPMetrics {
  total_duration_ms: number;
  time_to_first_event_ms?: number;
  event_count: number;
  events_per_second?: number;
}

export interface KurralMCPCall {
  id: string;
  timestamp: string;
  source: 'mcp';
  server: string;
  method: string;
  tool_name?: string;
  arguments: Record<string, any>;
  result?: any;
  error?: Record<string, any>;
  was_sse: boolean;
  events?: MCPEvent[];
  duration_ms: number;
  request_id?: string;
  metrics?: MCPMetrics;
}

export interface LLMConfig {
  model_name: string;
  provider: string;
  parameters: Record<string, any>;
}

export interface GraphVersion {
  graph_hash: string;
  tool_schemas_hash: string;
}

export interface ResolvedPrompt {
  template: string;
  template_hash: string;
  variables: Record<string, any>;
  variables_hash: string;
}

export interface Interaction {
  input: string;
  output?: string;
}

export interface PerToolARS {
  tool_id: string;
  tool_name: string;
  ars_score: number;
  match_status: 'exact' | 'near_match' | 'mismatch';
  output_diff?: {
    field: string;
    original: any;
    replay: any;
    difference: string;
  } | null;
}

export interface ReplayInfo {
  ars_score: number;
  determinism_score: number;
  total_tool_calls: number;
  stubbed_calls: number;
  live_calls: number;
  per_tool_ars?: PerToolARS[];
  comparison_notes?: string;
}

export interface KurralArtifact {
  kurral_id: string;
  run_id: string;
  tenant_id: string;
  environment: string;
  schema_version: string;
  created_at: string;
  deterministic: boolean;
  duration_ms: number;

  llm_config: LLMConfig;

  inputs: {
    interactions: Interaction[];
  };

  outputs: {
    interactions: Interaction[];
  };

  tool_calls: KurralToolCall[];

  // MCP-specific (optional)
  mcp_session_id?: string;
  mcp_servers_used?: string[];
  mcp_tool_calls?: KurralMCPCall[];

  // Replay metadata (optional)
  replay_mode?: 'level1' | 'level2';
  original_artifact_id?: string;
  ars_score?: number;
  determinism_score?: number;
  replay_info?: ReplayInfo;

  graph_version: GraphVersion;
  resolved_prompt: ResolvedPrompt;
}

// Summary for list views
export interface ArtifactSummary {
  kurral_id: string;
  run_id: string;
  created_at: string;
  duration_ms: number;
  tool_count: number;
  model_name: string;
  has_mcp: boolean;
  ars_score?: number;
}
