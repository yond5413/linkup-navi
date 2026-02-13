export interface CommandRequest {
  command: string;
  files: string[];
  sessionId?: string;
  researchEntities?: string[];
}

export interface BriefingOutput {
  summary: string;
  deadlines: string[];
  risks: string[];
  research?: LinkupResult;
  actions?: string[];
}

// New dynamic response structure
export interface ResponseSection {
  id: string;
  title: string;
  content: string;
}

export interface DynamicOutput {
  query_type: string;
  query_type_label: string;
  thought?: string; // High-level reasoning
  sections: ResponseSection[];
  raw_response: string;
  structured: boolean;
  research_metadata?: ResearchMetadata;
}

export interface LinkupResult {
  entity: string;
  snippets: string[];
  url?: string;
}

export interface ResearchSource {
  entity: string;
  url: string;
  title: string;
  snippet: string;
  favicon?: string;
}

export interface ResearchMetadata {
  entities: string[];
  sources: ResearchSource[];
  auto_researched: boolean;
}

export interface Session {
  id: string;
  command: string;
  files: string[];
  output: BriefingOutput | DynamicOutput | null;
  createdAt: Date;
}

export interface FileUpload {
  name: string;
  size: number;
  type: string;
  url?: string;
}

export interface ExecutionStatus {
  session_id: string;
  current_step: string;
  reasoning: string;
  thought: string; // The agent's current internal thought
  progress: number;
  complete: boolean;
  timestamp?: string;
}

export interface ClarificationOption {
  type: string;
  label: string;
  confidence: number;
}

export type ExecutionStep =
  | "Planning"
  | "Analyzing documents"
  | "Extracting deadlines"
  | "Extracting skills"
  | "Researching entities"
  | "Synthesizing briefing"
  | "Generating response"
  | "Complete"
  | "Waiting";

export interface TaskExecutionDetail {
  tool: string;
  observation: string;
  timestamp: string;
}

export interface CompletedStep {
  step: number;
  tool: string;
  success: boolean;
  error?: string;
}

export interface TaskExecutionDetails {
  execution_trace: TaskExecutionDetail[];
  iterations: number;
  artifacts_keys: string[];
  completed_steps: (CompletedStep | string)[];
}

export interface Task {
  task_id: string;
  session_id: string;
  user_input: string;
  inferred_intent: string;
  tools_used: string;
  status: string;
  timestamp: string;
  execution_details?: string;
}

export interface TaskDetail extends Task {
  executionDetailsParsed?: TaskExecutionDetails;
}
