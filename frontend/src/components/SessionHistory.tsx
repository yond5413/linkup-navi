"use client";

import { useState, useEffect, useRef } from "react";
import { Plus, Clock, X, Pencil } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { SessionInfo, getSessions, createSession, deleteSession, updateSession } from "@/lib/api";

interface SessionHistoryProps {
  currentSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;
  onNewSession: () => void;
}

export function SessionHistory({
  currentSessionId,
  onSessionSelect,
  onNewSession,
}: SessionHistoryProps) {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [hoveredSession, setHoveredSession] = useState<string | null>(null);
  const [deletingSession, setDeletingSession] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const editInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    if (editingId && editInputRef.current) {
      editInputRef.current.focus();
      editInputRef.current.select();
    }
  }, [editingId]);

  const loadSessions = async () => {
    try {
      const data = await getSessions();
      setSessions(data);
    } catch (error) {
      console.error("Failed to load sessions:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleNewSession = async () => {
    try {
      const session = await createSession();
      setSessions([session, ...sessions]);
      onNewSession();
    } catch (error) {
      console.error("Failed to create session:", error);
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    setDeletingSession(sessionId);
  };

  const confirmDelete = async () => {
    if (!deletingSession) return;
    try {
      await deleteSession(deletingSession);
      setSessions(sessions.filter((s) => s.id !== deletingSession));
    } catch (error) {
      console.error("Failed to delete session:", error);
    } finally {
      setDeletingSession(null);
    }
  };

  const cancelDelete = () => {
    setDeletingSession(null);
  };

  const handleEditStart = (session: SessionInfo, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(session.id);
    setEditValue(session.user_goal || "");
  };

  const handleEditSave = async (sessionId: string) => {
    if (!editValue.trim()) {
      setEditingId(null);
      return;
    }
    try {
      await updateSession(sessionId, { user_goal: editValue });
      setSessions(
        sessions.map((s) =>
          s.id === sessionId ? { ...s, user_goal: editValue } : s
        )
      );
    } catch (error) {
      console.error("Failed to update session:", error);
    } finally {
      setEditingId(null);
    }
  };

  const handleEditCancel = () => {
    setEditingId(null);
    setEditValue("");
  };

  const handleEditKeyDown = (e: React.KeyboardEvent, sessionId: string) => {
    if (e.key === "Enter") {
      handleEditSave(sessionId);
    } else if (e.key === "Escape") {
      handleEditCancel();
    }
  };

  const handleClickOutside = (e: MouseEvent) => {
    if (editingId && e.target instanceof HTMLElement && !e.target.closest(".session-item")) {
      handleEditCancel();
    }
  };

  useEffect(() => {
    if (editingId) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [editingId]);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getGoalPreview = (goal?: string) => {
    if (!goal) return "New session";
    return goal.length > 30 ? goal.slice(0, 30) + "..." : goal;
  };

  return (
    <div className="w-64 bg-white border-r border-slate-200 h-screen flex flex-col">
      {deletingSession && (
        <div className="absolute inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 shadow-lg max-w-sm mx-4">
            <h3 className="font-semibold text-slate-900 mb-2">Delete Session?</h3>
            <p className="text-sm text-slate-600 mb-4">
              This will permanently delete this session and all its files. This action cannot be undone.
            </p>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={cancelDelete}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={confirmDelete}>
                Delete
              </Button>
            </div>
          </div>
        </div>
      )}

      <div className="p-4 border-b border-slate-200">
        <Button onClick={handleNewSession} className="w-full" size="sm">
          <Plus className="h-4 w-4 mr-2" />
          New Session
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="p-3">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Sessions
          </h3>

          {loading ? (
            <div className="text-sm text-slate-400">Loading...</div>
          ) : sessions.length === 0 ? (
            <div className="text-sm text-slate-400">No sessions yet</div>
          ) : (
            <div className="space-y-1">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  onMouseEnter={() => setHoveredSession(session.id)}
                  onMouseLeave={() => setHoveredSession(null)}
                  className={`group relative flex items-center gap-2 w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    currentSessionId === session.id
                      ? "bg-slate-100 text-slate-900"
                      : "hover:bg-slate-50 text-slate-600"
                  }`}
                >
                  {editingId === session.id ? (
                    <input
                      ref={editInputRef}
                      type="text"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onKeyDown={(e) => handleEditKeyDown(e, session.id)}
                      onClick={(e) => e.stopPropagation()}
                      className="flex-1 min-w-0 px-1 py-0.5 text-sm border border-slate-300 rounded bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400"
                      placeholder="Session name..."
                    />
                  ) : (
                    <button
                      onClick={() => onSessionSelect(session.id)}
                      className="flex-1 min-w-0 session-item"
                    >
                      <div className="font-medium truncate">
                        {getGoalPreview(session.user_goal)}
                      </div>
                      <div className="flex items-center gap-1 text-xs text-slate-400 mt-1">
                        <Clock className="h-3 w-3" />
                        {formatDate(session.created_at)}
                      </div>
                    </button>
                  )}

                  {hoveredSession === session.id && editingId !== session.id && (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => handleEditStart(session, e)}
                        className="p-1 rounded hover:bg-slate-200 text-slate-400 hover:text-slate-600 transition-colors"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteSession(session.id);
                        }}
                        className="p-1 rounded hover:bg-slate-200 text-slate-400 hover:text-red-500 transition-colors"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  )}

                  {editingId === session.id && (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleEditSave(session.id)}
                        className="p-1 rounded hover:bg-green-100 text-green-600 transition-colors"
                      >
                        <span className="text-xs font-medium">Save</span>
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleEditCancel();
                        }}
                        className="p-1 rounded hover:bg-slate-200 text-slate-400 transition-colors"
                      >
                        <span className="text-xs font-medium">Cancel</span>
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
