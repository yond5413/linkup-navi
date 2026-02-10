"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { CommandInput } from "@/components/CommandInput";
import { FileUploader } from "@/components/FileUploader";
import { OutputPanel } from "@/components/OutputPanel";
import { SessionHistory } from "@/components/SessionHistory";
import { ExecutionStatusDisplay } from "@/components/ExecutionStatus";
import { ClarificationModal } from "@/components/ClarificationModal";
import { BriefingOutput, DynamicOutput, FileUpload, ExecutionStatus, ClarificationOption } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { BrainCircuit } from "lucide-react";
import {
  createSession,
  getSession,
  executePrep,
  clarifyQuery,
  getExecutionStatus,
  transformResponse,
  transformBriefing,
  isClarificationResponse,
  SessionInfo,
  ApiResponse,
  PrepResponse,
} from "@/lib/api";

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [command, setCommand] = useState("");
  const [files, setFiles] = useState<FileUpload[]>([]);
  const [output, setOutput] = useState<BriefingOutput | DynamicOutput | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [executionStatus, setExecutionStatus] = useState<ExecutionStatus | null>(null);
  
  // Clarification state
  const [clarificationNeeded, setClarificationNeeded] = useState(false);
  const [clarificationOptions, setClarificationOptions] = useState<ClarificationOption[]>([]);
  const [clarificationMessage, setClarificationMessage] = useState("");
  const [pendingCommand, setPendingCommand] = useState("");
  
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    initSession();
  }, []);

  const initSession = async () => {
    try {
      const session = await createSession();
      setSessionId(session.id);
    } catch (err) {
      setError("Failed to initialize session");
    }
  };

  const handleNewSession = () => {
    setSessionId(null);
    setFiles([]);
    setOutput(null);
    setCommand("");
    setClarificationNeeded(false);
    initSession();
  };

  const handleSessionSelect = async (id: string) => {
    setSessionId(id);
    setFiles([]);
    setOutput(null);
    setCommand("");
    setClarificationNeeded(false);

    try {
      const session = await getSession(id);
      setFiles(
        session.files.map((f) => ({
          name: f.file_name,
          size: 0,
          type: f.file_type,
        }))
      );
    } catch (err) {
      console.error("Failed to load session:", err);
    }
  };

  // Polling for execution status
  useEffect(() => {
    if (isLoading && sessionId) {
      // Start polling
      pollingRef.current = setInterval(async () => {
        try {
          const status = await getExecutionStatus(sessionId);
          setExecutionStatus(status);
        } catch (err) {
          console.error("Failed to fetch execution status:", err);
        }
      }, 1000); // Poll every 1 second
    } else {
      // Stop polling
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
    
    setClarificationNeeded(false);
    setIsLoading(true);
    setError(null);
    setExecutionStatus(null);

    try {
      const response = await clarifyQuery(sessionId, pendingCommand, selectedType);
      const transformed = transformResponse(response);
      setOutput(transformed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
      setOutput(null);
    } finally {
      setIsLoading(false);
      setPendingCommand("");
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
      setCommand(cmd);
      setExecutionStatus(null);
      setClarificationNeeded(false);

      try {
        const response: ApiResponse = await executePrep(sessionId, cmd, researchEntities);
        
        // Check if clarification is needed
        if (isClarificationResponse(response)) {
          setClarificationNeeded(true);
          setClarificationOptions(response.suggested_types);
          setClarificationMessage(response.message);
          setPendingCommand(cmd);
          setIsLoading(false);
          return;
        }
        
        // Normal response flow
        const transformed = transformResponse(response);
        setOutput(transformed);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
        setOutput(null);
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId]
  );

  return (
    <div className="min-h-screen bg-[#0f172a] flex text-slate-200">
      <div className="w-80 border-r border-slate-800 bg-slate-900/50 backdrop-blur-xl">
        <SessionHistory
          currentSessionId={sessionId}
          onSessionSelect={handleSessionSelect}
          onNewSession={handleNewSession}
        />
      </div>

      <div className="flex-1 flex flex-col">
        <header className="bg-slate-900/40 border-b border-slate-800 backdrop-blur-md sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-4">
            <div className="p-2.5 bg-blue-600 rounded-xl shadow-lg shadow-blue-500/20">
              <BrainCircuit className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">
                Linkup Navi
              </h1>
              <p className="text-xs text-slate-400 font-medium">AGI intelligence Engine</p>
            </div>
            {sessionId && (
              <div className="ml-auto flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/50 border border-slate-700">
                <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-xs text-slate-300 font-mono">
                  {sessionId.slice(0, 8)}
                </span>
              </div>
            )}
          </div>
        </header>

        <main className="flex-1 max-w-7xl mx-auto px-4 py-8 w-full">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-6">
              <Card className="glass-card border-slate-700 overflow-hidden">
                <CardHeader className="bg-slate-800/30 border-b border-slate-700">
                  <CardTitle className="text-slate-200">Intelligence Command</CardTitle>
                </CardHeader>
                <CardContent className="pt-6">
                  <CommandInput
                    onSubmit={handleSubmit}
                    isLoading={isLoading}
                  />
                </CardContent>
              </Card>

              <Card className="glass-card border-slate-700 overflow-hidden font-sans">
                <CardHeader className="bg-slate-800/30 border-b border-slate-700">
                  <CardTitle className="text-slate-200 text-lg">Knowledge Base</CardTitle>
                </CardHeader>
                <CardContent className="pt-6">
                  <FileUploader
                    sessionId={sessionId || ""}
                    files={files}
                    onFilesChange={setFiles}
                  />
                </CardContent>
              </Card>

              {error && (
                <Card className="border-red-200 bg-red-50">
                  <CardContent className="py-4">
                    <p className="text-red-600 text-sm">{error}</p>
                  </CardContent>
                </Card>
              )}
            </div>

            <div className="space-y-6">
              {isLoading ? (
                <Card className="glass-card border-slate-700 overflow-hidden">
                  <CardHeader className="bg-slate-800/30 border-b border-slate-700">
                    <CardTitle className="text-slate-200">Processing</CardTitle>
                  </CardHeader>
                  <CardContent className="pt-6">
                    {executionStatus ? (
                      <ExecutionStatusDisplay status={executionStatus} />
                    ) : (
                      <div className="flex items-center justify-center py-8">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400 mr-3" />
                        <span className="text-slate-400">Initializing...</span>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ) : (
                <>
                  {clarificationNeeded && (
                    <ClarificationModal
                      message={clarificationMessage}
                      options={clarificationOptions}
                      onSelect={handleClarificationSelect}
                    />
                  )}
                  <OutputPanel output={output} isLoading={isLoading} />
                </>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
