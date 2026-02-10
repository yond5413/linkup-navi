"use client";

import { useEffect, useState } from "react";
import { AdminSidebar } from "@/components/AdminSidebar";

interface Task {
  task_id: string;
  session_id: string;
  user_input: string;
  inferred_intent: string;
  tools_used: string;
  status: string;
  timestamp: string;
}

export default function AdminTasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchTasks() {
      try {
        const res = await fetch("http://localhost:8000/api/v1/admin/tasks");
        if (!res.ok) throw new Error("Failed to fetch tasks");
        const data = await res.json();
        setTasks(data.tasks || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }
    fetchTasks();
  }, []);

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      success: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
      error: "bg-red-500/20 text-red-400 border-red-500/30",
      in_progress: "bg-amber-500/20 text-amber-400 border-amber-500/30",
      pending: "bg-slate-500/20 text-slate-400 border-slate-500/30",
    };
    return colors[status] || colors.pending;
  };

  if (loading) {
    return (
      <div className="min-h-screen">
        <div className="pr-16 min-h-screen p-8">
          <div className="glass-card rounded-xl p-8 animate-pulse max-w-7xl">
            <div className="h-6 bg-white/10 rounded w-1/4 mb-4"></div>
            <div className="space-y-3">
              <div className="h-4 bg-white/10 rounded w-full"></div>
              <div className="h-4 bg-white/10 rounded w-5/6"></div>
              <div className="h-4 bg-white/10 rounded w-4/6"></div>
            </div>
          </div>
        </div>
        <AdminSidebar />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen">
        <div className="pr-16 min-h-screen p-8">
          <div className="glass-card rounded-xl p-8 text-center max-w-7xl mx-auto">
            <p className="text-red-400">Error: {error}</p>
            <p className="text-slate-400 mt-2">Make sure the backend server is running on port 8000</p>
          </div>
        </div>
        <AdminSidebar />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="pr-16 min-h-screen p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold mb-6">Agent Task History</h1>

          {tasks.length === 0 ? (
            <div className="glass-card rounded-xl p-12 text-center">
              <p className="text-slate-400 text-lg">No tasks recorded yet</p>
              <p className="text-slate-500 mt-2">Tasks will appear here as agents execute queries</p>
            </div>
          ) : (
            <div className="glass-card rounded-xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-white/5 border-b border-white/10">
                    <tr>
                      <th className="p-4 font-medium text-slate-300">Task ID</th>
                      <th className="p-4 font-medium text-slate-300">User Input</th>
                      <th className="p-4 font-medium text-slate-300">Intent</th>
                      <th className="p-4 font-medium text-slate-300">Tools</th>
                      <th className="p-4 font-medium text-slate-300">Status</th>
                      <th className="p-4 font-medium text-slate-300">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {tasks.map((task) => (
                      <tr key={task.task_id} className="hover:bg-white/5 transition-colors">
                        <td className="p-4 font-mono text-xs text-slate-400 max-w-[120px] truncate">
                          {task.task_id}
                        </td>
                        <td className="p-4 text-slate-200 max-w-[200px] truncate" title={task.user_input}>
                          {task.user_input || "-"}
                        </td>
                        <td className="p-4 text-slate-300 max-w-[150px] truncate" title={task.inferred_intent}>
                          {task.inferred_intent || "-"}
                        </td>
                        <td className="p-4 text-slate-400 max-w-[150px] truncate" title={task.tools_used}>
                          {task.tools_used || "-"}
                        </td>
                        <td className="p-4">
                          <span className={`px-2 py-1 rounded-full text-xs border ${getStatusBadge(task.status)}`}>
                            {task.status}
                          </span>
                        </td>
                        <td className="p-4 text-slate-400 text-xs whitespace-nowrap">
                          {task.timestamp ? new Date(task.timestamp).toLocaleString() : "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
        <AdminSidebar />
      </div>
    </div>
  );
}
