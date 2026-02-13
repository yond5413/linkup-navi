const API_BASE = "http://localhost:8000/api/v1";

export interface ExecutionStatus {
  session_id: string;
  current_step: string;
  reasoning: string;
  thought: string;
  progress: number;
  complete: boolean;
  timestamp?: string;
}

export interface BriefingResponse {
  summary: string;
  deadlines: string[];
  risks: string[];
  research_snippet: string;
  actionable_briefing: string;
}

export interface DynamicResponse {
  query_type: string;
  sections: Record<string, string>;
  raw_response: string;
  structured: boolean;
}

export interface ClarificationOption {
  type: string;
  label: string;
  confidence: number;
}

export interface ClarificationResponse {
  status: "needs_clarification";
  message: string;
  suggested_types: ClarificationOption[];
  original_query: string;
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

// Re-export from types for consistency
export type { ResearchSource as ResearchSourceType } from "@/types";

export interface PrepResponse {
  status?: "success";
  session_id: string;
  intent: string;
  query_type: string;
  plan: Record<string, unknown>;
  results: Record<string, unknown>;
  response: DynamicResponse;
  evaluation?: Record<string, unknown>;
  research_metadata?: ResearchMetadata;
}

export interface UploadResponse {
  file_id: string;
  file_name: string;
  session_id: string;
  message: string;
}

export interface SessionInfo {
  id: string;
  created_at: string;
  updated_at: string;
  user_goal?: string;
}

export interface SessionDetail extends SessionInfo {
  files: Array<{
    id: string;
    file_name: string;
    file_type: string;
    uploaded_at: string;
  }>;
}

export type ApiResponse = PrepResponse | ClarificationResponse;

export async function createSession(): Promise<SessionInfo> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to create session");
  return res.json();
}

export async function getSessions(): Promise<SessionInfo[]> {
  const res = await fetch(`${API_BASE}/sessions`);
  if (!res.ok) throw new Error("Failed to fetch sessions");
  const data = await res.json();
  return data.sessions;
}

export async function getSession(sessionId: string): Promise<SessionDetail> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!res.ok) throw new Error("Failed to fetch session");
  return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete session");
}

export async function updateSession(
  sessionId: string,
  updates: { user_goal: string }
): Promise<void> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error("Failed to update session");
}

export async function uploadFile(
  sessionId: string,
  file: File
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/upload?session_id=${sessionId}`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Failed to upload file");
  return res.json();
}

export async function executePrep(
  sessionId: string,
  command: string,
  researchEntities?: string[]
): Promise<ApiResponse> {
  const res = await fetch(`${API_BASE}/prep`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      command,
      file_refs: [],
      research_entities: researchEntities,
    }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to execute prep");
  }
  return res.json();
}

export async function clarifyQuery(
  sessionId: string,
  originalCommand: string,
  selectedType: string
): Promise<PrepResponse> {
  const res = await fetch(`${API_BASE}/clarify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      original_command: originalCommand,
      selected_type: selectedType,
    }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to clarify query");
  }
  return res.json();
}

export async function getHealth() {
  const res = await fetch("http://localhost:8000/health");
  return res.json();
}

export async function getExecutionStatus(sessionId: string): Promise<ExecutionStatus> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/execution-status`);
  if (!res.ok) throw new Error("Failed to fetch execution status");
  return res.json();
}

// Output persistence API
export async function getSessionMessages(sessionId: string): Promise<any[]> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`);
  if (!res.ok) throw new Error("Failed to fetch session messages");
  const data = await res.json();
  return data.messages;
}

export async function getSessionOutput(sessionId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/output`);
  if (!res.ok) throw new Error("Failed to fetch session output");
  const data = await res.json();
  return data.output;
}

export function transformPersistedOutput(data: any) {
  if (!data) return null;

  // Transform sections record to array
  const sections = Object.entries(data.sections || {}).map(([key, content]) => ({
    id: key,
    title: formatSectionTitle(key),
    content: content as string,
  }));

  return {
    query_type: data.query_type,
    query_type_label: formatQueryTypeLabel(data.query_type),
    thought: data.thought || "",
    sections,
    raw_response: data.raw_response,
    structured: data.structured,
    research_metadata: data.research_metadata,
  };
}

export async function getAllFiles(): Promise<Array<{ id: string; session_id: string; file_name: string; file_type: string; uploaded_at: string }>> {
  const res = await fetch(`${API_BASE}/knowledge/files`);
  if (!res.ok) throw new Error("Failed to fetch knowledge base files");
  const data = await res.json();
  return data.files;
}

export async function getMemoryStatus(): Promise<{ total_chunks: number; index_name: string }> {
  const res = await fetch(`${API_BASE}/knowledge/memory-status`);
  if (!res.ok) throw new Error("Failed to fetch memory status");
  return res.json();
}

export interface MemoryStats {
  total_vectors: number;
  index_name: string;
  cohere_configured: boolean;
}

export interface MemoryChunk {
  text: string;
  index: number;
}

export interface MemorySearchResult {
  text: string;
  score: number;
  rank: number;
}

export async function getMemoryStats(): Promise<MemoryStats> {
  const res = await fetch(`${API_BASE}/admin/memory/stats`);
  if (!res.ok) throw new Error("Failed to fetch memory stats");
  return res.json();
}

export async function getRecentChunks(limit: number): Promise<MemoryChunk[]> {
  const res = await fetch(`${API_BASE}/admin/memory/recent?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch recent chunks");
  const data = await res.json();
  return data.chunks;
}

export async function searchMemory(query: string, k: number): Promise<MemorySearchResult[]> {
  const params = new URLSearchParams({ query, k: k.toString() });
  const res = await fetch(`${API_BASE}/admin/memory/search?${params}`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to search memory");
  }
  const data = await res.json();
  return data.results;
}

export interface ModelInfo {
  id: string;
  name: string;
}

export interface ModelResponse {
  current: ModelInfo;
  available: ModelInfo[];
}

export async function getCurrentModel(): Promise<ModelResponse> {
  const res = await fetch(`${API_BASE}/admin/model`);
  if (!res.ok) throw new Error("Failed to fetch model");
  return res.json();
}

export async function setCurrentModel(modelId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/admin/model`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: modelId }),
  });
  if (!res.ok) throw new Error("Failed to set model");
}

export async function deleteKnowledgeFile(fileId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/knowledge/files/${fileId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete file from knowledge base");
}

export function isClarificationResponse(response: ApiResponse): response is ClarificationResponse {
  return "status" in response && response.status === "needs_clarification";
}

export function transformResponse(response: PrepResponse) {
  // Transform the dynamic response into a format the UI can render
  const { response: dynamicResponse, research_metadata } = response;

  // Convert sections into an array for rendering
  const sections = Object.entries(dynamicResponse.sections).map(([key, content]) => ({
    id: key,
    title: formatSectionTitle(key),
    content,
  }));

  // Plan-level reasoning (from orchestrator)
  const planThought = (response as any).plan?.thought || "";

  return {
    query_type: dynamicResponse.query_type,
    query_type_label: formatQueryTypeLabel(dynamicResponse.query_type),
    thought: planThought,
    sections,
    raw_response: dynamicResponse.raw_response,
    structured: dynamicResponse.structured,
    research_metadata,
  };
}

function formatSectionTitle(key: string): string {
  // Convert snake_case to Title Case
  return key
    .split("_")
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function formatQueryTypeLabel(queryType: string): string {
  const labels: Record<string, string> = {
    "resume_review": "Resume Review",
    "meeting_prep": "Meeting Preparation",
    "contract_review": "Contract Review",
    "document_analysis": "Document Analysis",
    "comparison": "Document Comparison",
    "general_qa": "General Analysis",
  };
  return labels[queryType] || "Analysis";
}

// Legacy transform function for backward compatibility
export function transformBriefing(response: PrepResponse) {
  // This is a fallback that creates the old structure from the new response
  const { response: dynamicResponse } = response;

  return {
    summary: dynamicResponse.sections.executive_summary || dynamicResponse.sections.summary || dynamicResponse.raw_response,
    deadlines: [],
    risks: [],
    research: {
      entity: "Analysis",
      snippets: [],
    },
    actions: [],
  };
}

export interface TaskDetailResponse {
  task_id: string;
  session_id: string;
  user_input: string;
  inferred_intent: string;
  tools_used: string;
  status: string;
  timestamp: string;
  execution_details: string;
}

export async function fetchTaskDetail(taskId: string): Promise<TaskDetailResponse> {
  const res = await fetch(`${API_BASE}/admin/tasks/${taskId}`);
  if (!res.ok) throw new Error("Failed to fetch task details");
  const data = await res.json();
  return data.task;
}
