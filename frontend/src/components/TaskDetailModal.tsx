"use client";

import { useEffect, useState } from "react";
import { fetchTaskDetail, TaskDetailResponse } from "@/lib/api";
import { TaskExecutionDetails } from "@/types";
import { Button } from "@/components/ui/Button";
import { X, RefreshCw, Box, ListChecks, Clock } from "lucide-react";

interface TaskDetailModalProps {
  taskId: string;
  onClose: () => void;
}

export function TaskDetailModal({ taskId, onClose }: TaskDetailModalProps) {
  const [task, setTask] = useState<TaskDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadTaskDetail() {
      try {
        const data = await fetchTaskDetail(taskId);
        setTask(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load task details");
      } finally {
        setLoading(false);
      }
    }
    loadTaskDetail();
  }, [taskId]);

  const parseExecutionDetails = (): TaskExecutionDetails | null => {
    if (!task?.execution_details) return null;
    try {
      return JSON.parse(task.execution_details);
    } catch {
      return null;
    }
  };

  const executionDetails = parseExecutionDetails();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-4xl max-h-[85vh] overflow-hidden bg-slate-900 border border-slate-700 rounded-xl shadow-2xl flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-slate-100">Task Execution Details</h2>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-8 w-8 animate-spin text-slate-400" />
            </div>
          )}

          {error && (
            <div className="text-center py-12">
              <p className="text-red-400">Error: {error}</p>
            </div>
          )}

          {!loading && !error && task && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-800/50 rounded-lg p-4">
                  <p className="text-xs text-slate-500 mb-1">Task ID</p>
                  <p className="font-mono text-sm text-slate-300 break-all">{task.task_id}</p>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-4">
                  <p className="text-xs text-slate-500 mb-1">Session ID</p>
                  <p className="font-mono text-sm text-slate-300 break-all">{task.session_id}</p>
                </div>
              </div>

              <div className="bg-slate-800/50 rounded-lg p-4">
                <p className="text-xs text-slate-500 mb-1">User Input</p>
                <p className="text-slate-200">{task.user_input}</p>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="bg-slate-800/50 rounded-lg p-4">
                  <p className="text-xs text-slate-500 mb-1">Inferred Intent</p>
                  <p className="text-slate-300 text-sm">{task.inferred_intent || "-"}</p>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-4">
                  <p className="text-xs text-slate-500 mb-1">Tools Used</p>
                  <p className="text-slate-300 text-sm">{task.tools_used}</p>
                </div>
                <div className="bg-slate-800/50 rounded-lg p-4">
                  <p className="text-xs text-slate-500 mb-1">Status</p>
                  <span className={`px-2 py-1 rounded-full text-xs border ${
                    task.status === "success" ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" :
                    task.status === "error" ? "bg-red-500/20 text-red-400 border-red-500/30" :
                    "bg-amber-500/20 text-amber-400 border-amber-500/30"
                  }`}>
                    {task.status}
                  </span>
                </div>
              </div>

              {executionDetails && (
                <>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-slate-800/50 rounded-lg p-4 flex items-center gap-3">
                      <Clock className="h-5 w-5 text-blue-400" />
                      <div>
                        <p className="text-xs text-slate-500">Iterations</p>
                        <p className="text-xl font-semibold text-slate-200">{executionDetails.iterations}</p>
                      </div>
                    </div>
                    <div className="bg-slate-800/50 rounded-lg p-4 flex items-center gap-3">
                      <Box className="h-5 w-5 text-purple-400" />
                      <div>
                        <p className="text-xs text-slate-500">Artifacts</p>
                        <p className="text-xl font-semibold text-slate-200">{executionDetails.artifacts_keys?.length || 0}</p>
                      </div>
                    </div>
                    <div className="bg-slate-800/50 rounded-lg p-4 flex items-center gap-3">
                      <ListChecks className="h-5 w-5 text-emerald-400" />
                      <div>
                        <p className="text-xs text-slate-500">Completed Steps</p>
                        <p className="text-xl font-semibold text-slate-200">{executionDetails.completed_steps?.length || 0}</p>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-medium text-slate-300 mb-3">Execution Trace (Tool Calls)</h3>
                    <div className="space-y-2 max-h-[300px] overflow-y-auto">
                      {executionDetails.execution_trace?.length > 0 ? (
                        executionDetails.execution_trace.map((step, idx) => (
                          <div key={idx} className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/50">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-medium text-blue-400 text-sm">{step.tool}</span>
                              <span className="text-xs text-slate-500">
                                {step.timestamp ? new Date(step.timestamp).toLocaleString() : "-"}
                              </span>
                            </div>
                            <p className="text-sm text-slate-400">{step.observation}</p>
                          </div>
                        ))
                      ) : (
                        <p className="text-slate-500 text-sm">No execution trace available</p>
                      )}
                    </div>
                  </div>

                  {executionDetails.completed_steps && executionDetails.completed_steps.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-slate-300 mb-3">Completed Steps</h3>
                      <div className="flex flex-wrap gap-2">
                        {executionDetails.completed_steps.map((step, idx) => {
                          // Defensive: handle both string format (legacy) and object format (new)
                          if (typeof step === 'string') {
                            return (
                              <span
                                key={idx}
                                className="px-3 py-1 bg-slate-500/20 text-slate-400 rounded-full text-xs border border-slate-500/30"
                              >
                                {step}
                              </span>
                            );
                          }
                          // Object format with step, tool, success properties
                          return (
                            <span
                              key={idx}
                              className={`px-3 py-1 rounded-full text-xs border ${
                                step.success 
                                  ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                                  : "bg-red-500/20 text-red-400 border-red-500/30"
                              }`}
                              title={step.error || `Step ${step.step}`}
                            >
                              {step.tool} #{step.step}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {executionDetails.artifacts_keys && executionDetails.artifacts_keys.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-slate-300 mb-3">Artifacts Created</h3>
                      <div className="flex flex-wrap gap-2">
                        {executionDetails.artifacts_keys.map((key, idx) => (
                          <span
                            key={idx}
                            className="px-3 py-1 bg-purple-500/20 text-purple-400 rounded-full text-xs border border-purple-500/30"
                          >
                            {key}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}

              {!executionDetails && (
                <div className="text-center py-8 text-slate-500">
                  No execution details available for this task
                </div>
              )}
            </div>
          )}
        </div>

        <div className="p-4 border-t border-slate-700">
          <Button onClick={onClose} className="w-full">
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}
