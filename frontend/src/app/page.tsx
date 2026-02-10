"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { CommandInput } from "@/components/CommandInput";
import { OutputPanel } from "@/components/OutputPanel";
import { SessionHistory } from "@/components/SessionHistory";
import { ChatThread } from "@/components/ChatThread";
import { BriefingOutput, DynamicOutput, FileUpload, ExecutionStatus, ClarificationOption } from "@/types";
import { BrainCircuit, ChevronRight, ChevronLeft } from "lucide-react";
import { AdminSidebar } from "@/components/AdminSidebar";
import {
  createSession,
  getSession,
  executePrep,
  clarifyQuery,
  getExecutionStatus,
  transformResponse,
  isClarificationResponse,
  getSessionMessages,
  getSessionOutput,
  transformPersistedOutput,
  ApiResponse,
} from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  type: "text" | "status" | "clarification";
  status?: ExecutionStatus | null;
  clarification?: {
    message: string;
    options: ClarificationOption[];
  };
}

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [files, setFiles] = useState<FileUpload[]>([]);
  const [output, setOutput] = useState<BriefingOutput | DynamicOutput | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [executionStatus, setExecutionStatus] = useState<ExecutionStatus | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);

  const [sidebarsCollapsed, setSidebarsCollapsed] = useState({ left: false });

  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    initSession();
  }, []);

  const initSession = async () => {
    try {
      const savedSessionId = localStorage.getItem("linkup_session_id");
      if (savedSessionId) {
        setSessionId(savedSessionId);
        handleSessionSelect(savedSessionId);
      } else {
        const session = await createSession();
        setSessionId(session.id);
        localStorage.setItem("linkup_session_id", session.id);
        setMessages([]);
        setOutput(null);
      }
    } catch (err) {
      console.error("Session init failed:", err);
      // Only clear if strictly necessary, or maybe just start fresh
      // localStorage.removeItem("linkup_session_id");
    }
  };

  const handleNewSession = async () => {
    setIsLoading(true);
    try {
      const session = await createSession();
      setSessionId(session.id);
      localStorage.setItem("linkup_session_id", session.id);
      setFiles([]);
      setOutput(null);
      setMessages([]);
    } catch (err) {
      setError("Failed to create new session");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSessionSelect = async (id: string) => {
    setSessionId(id);
    localStorage.setItem("linkup_session_id", id);
    setFiles([]);
    setOutput(null);
    setMessages([]);

    try {
      const [session, loadedMessages, loadedOutput] = await Promise.all([
        getSession(id),
        getSessionMessages(id),
        getSessionOutput(id)
      ]);

      setFiles(
        session.files.map((f) => ({
          name: f.file_name,
          size: 0,
          type: f.file_type,
        }))
      );

      // Hydrate messages
      if (loadedMessages && loadedMessages.length > 0) {
        setMessages(loadedMessages.map(msg => ({
          id: msg.id,
          role: msg.role as "user" | "assistant",
          content: msg.content,
          type: (msg.type as any) || "text",
          status: null
        })));
      }

      // Hydrate output
      if (loadedOutput) {
        const transformed = transformPersistedOutput(loadedOutput);
        if (transformed) {
          setOutput(transformed);
        }
      }

    } catch (err) {
      console.error("Failed to load session:", err);
    }
  };

  useEffect(() => {
    if (isLoading && sessionId) {
      pollingRef.current = setInterval(async () => {
        try {
          const status = await getExecutionStatus(sessionId);
          setExecutionStatus(status);

          setMessages(prev => {
            const last = prev[prev.length - 1];
            if (last && last.type === "status") {
              return [...prev.slice(0, -1), { ...last, status }];
            }
            return prev;
          });
        } catch (err) {
          console.error("Failed to fetch execution status:", err);
        }
      }, 1000);
    } else {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [isLoading, sessionId]);

  const handleClarificationSelect = async (selectedType: string) => {
    if (!sessionId) return;

    setMessages(prev => prev.filter(m => m.type !== "clarification"));
    setIsLoading(true);
    setError(null);

    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: "user",
      content: `I meant: ${selectedType}`,
      type: "text"
    }]);

    try {
      const lastUserCommand = messages.filter(m => m.role === "user").pop()?.content || "";
      const response = await clarifyQuery(sessionId, lastUserCommand, selectedType);
      const transformed = transformResponse(response);

      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Briefing manifested in your workspace.`,
        type: "text"
      }]);

      setOutput(transformed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = useCallback(
    async (cmd: string, researchEntities?: string[]) => {
      if (!sessionId) {
        setError("No active session");
        return;
      }

      setIsLoading(true);
      setError(null);
      setExecutionStatus(null);

      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: "user",
        content: cmd,
        type: "text"
      }]);

      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Processing...",
        type: "status",
        status: null
      }]);

      try {
        const response: ApiResponse = await executePrep(sessionId, cmd, researchEntities);

        if (isClarificationResponse(response)) {
          setMessages(prev => [
            ...prev.filter(m => m.type !== "status"),
            {
              id: (Date.now() + 2).toString(),
              role: "assistant",
              content: response.message,
              type: "clarification",
              clarification: {
                message: response.message,
                options: response.suggested_types
              }
            }
          ]);
          setIsLoading(false);
          return;
        }

        const transformed = transformResponse(response);

        setMessages(prev => [
          ...prev.filter(m => m.type !== "status"),
          {
            id: (Date.now() + 3).toString(),
            role: "assistant",
            content: `Briefing manifested in your workspace.`,
            type: "text"
          }
        ]);

        setOutput(transformed);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
        setMessages(prev => prev.filter(m => m.type !== "status"));
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId, messages]
  );

  return (
    <div className="h-screen bg-[#0f172a] flex text-slate-200 overflow-hidden font-sans">
      {/* Session History Sidebar (Collapsible) */}
      <aside className={`transition-all duration-500 border-r border-slate-800/50 bg-slate-900/40 backdrop-blur-xl flex flex-col ${sidebarsCollapsed.left ? "w-0 opacity-0 overflow-hidden" : "w-72"
        }`}>
        <div className="p-6 flex items-center gap-3 border-b border-slate-800/50">
          <div className="p-2 bg-blue-600 rounded-xl shadow-lg shadow-blue-500/20">
            <BrainCircuit className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-tight uppercase">Linkup Navi</h1>
            <p className="text-[10px] text-slate-500 font-bold tracking-widest uppercase">Intelligence Engine</p>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          <SessionHistory
            currentSessionId={sessionId}
            onSessionSelect={handleSessionSelect}
            onNewSession={handleNewSession}
          />
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex overflow-hidden relative">
        {/* Toggle Left Sidebar */}
        <button
          onClick={() => setSidebarsCollapsed(prev => ({ ...prev, left: !prev.left }))}
          className="absolute left-4 top-1/2 -translate-y-1/2 z-20 h-12 w-6 bg-slate-800/50 hover:bg-slate-700 border border-slate-700 rounded-full flex items-center justify-center text-slate-400 transition-all opacity-0 hover:opacity-100"
        >
          {sidebarsCollapsed.left ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>

        <div className="flex-1 flex w-full">
          {/* Chat Column (Middle) */}
          <div className="flex-1 flex flex-col min-w-[400px] max-w-[45%] border-r border-slate-800/50 bg-slate-900/20">
            <header className="px-6 py-4 flex items-center justify-between border-b border-slate-800/50">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-xs font-mono text-slate-400 uppercase tracking-widest">Session: {sessionId?.slice(0, 8)}</span>
              </div>
              {error && (
                <span className="text-[10px] text-red-400 font-bold uppercase animate-pulse">{error}</span>
              )}
            </header>

            <ChatThread
              messages={messages}
              isLoading={isLoading}
              onClarify={handleClarificationSelect}
            />

            <div className="p-6 bg-gradient-to-t from-[#0f172a] via-[#0f172a] to-transparent">
              <CommandInput onSubmit={handleSubmit} isLoading={isLoading} />
            </div>
          </div>

          {/* Workspace Column (Right) */}
          <div className="flex-1 flex flex-col p-6 bg-slate-900/10 min-w-0">
            <OutputPanel
              output={output}
              isLoading={isLoading}
              onRefine={(prompt) => handleSubmit(prompt)}
              files={files}
              setFiles={setFiles}
              sessionId={sessionId || ""}
            />
          </div>
        </div>
      </main>

      {/* Fixed Admin Sidebar - we'll handle its layout purely in AdminSidebar.tsx next */}
      <AdminSidebar />
    </div>
  );
}
