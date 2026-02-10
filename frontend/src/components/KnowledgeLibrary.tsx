"use client";

import { useState, useEffect } from "react";
import { FileText, Database, RefreshCw, Layers } from "lucide-react";
import { getAllFiles, getMemoryStatus, deleteKnowledgeFile } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Trash2, Loader2 } from "lucide-react";

interface KnowledgeFile {
    id: string;
    session_id: string;
    file_name: string;
    file_type: string;
    uploaded_at: string;
}

export function KnowledgeLibrary() {
    const [files, setFiles] = useState<KnowledgeFile[]>([]);
    const [memoryStatus, setMemoryStatus] = useState<{ total_chunks: number; index_name: string } | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const [filesData, statusData] = await Promise.all([
                getAllFiles(),
                getMemoryStatus()
            ]);
            setFiles(filesData);
            setMemoryStatus(statusData);
        } catch (error) {
            console.error("Failed to load knowledge library:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleDelete = async (fileId: string) => {
        if (!confirm("Are you sure you want to delete this document? It will be removed from disk and memory.")) return;

        setDeletingId(fileId);
        try {
            await deleteKnowledgeFile(fileId);
            await loadData(); // Refresh list and stats
        } catch (error) {
            console.error("Failed to delete file:", error);
            alert("Failed to delete file");
        } finally {
            setDeletingId(null);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString() + " " + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Database className="h-4 w-4 text-blue-400" />
                    <span className="text-sm font-semibold text-slate-300">Persistent Knowledge</span>
                </div>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={loadData}
                    disabled={isLoading}
                    className="h-8 px-2 text-slate-400 hover:text-white"
                >
                    <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                </Button>
            </div>

            {memoryStatus && (
                <div className="grid grid-cols-2 gap-3">
                    <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-3">
                        <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-1">
                            <Layers className="h-3 w-3" />
                            <span>Vector Chunks</span>
                        </div>
                        <div className="text-xl font-bold text-blue-400">
                            {memoryStatus.total_chunks}
                        </div>
                    </div>
                    <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-3">
                        <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-1">
                            <FileText className="h-3 w-3" />
                            <span>Documents</span>
                        </div>
                        <div className="text-xl font-bold text-indigo-400">
                            {files.length}
                        </div>
                    </div>
                </div>
            )}

            <div className="space-y-2 pr-1">
                {isLoading && files.length === 0 ? (
                    <div className="text-center py-8 text-slate-500 text-sm">
                        <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2 text-blue-400/50" />
                        Discovering documents...
                    </div>
                ) : files.length === 0 ? (
                    <div className="text-center py-8 bg-slate-900/40 border border-dashed border-slate-800 rounded-xl">
                        <FileText className="h-8 w-8 text-slate-600 mx-auto mb-2 opacity-50" />
                        <p className="text-slate-500 text-sm px-4">No documents indexed in persistent memory yet.</p>
                    </div>
                ) : (
                    files.map((file) => (
                        <div
                            key={file.id}
                            className="group bg-slate-800/40 hover:bg-slate-800/80 border border-slate-700/50 rounded-xl p-3 transition-all duration-200"
                        >
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-slate-700/50 rounded-lg group-hover:bg-blue-500/10 transition-colors">
                                    <FileText className="h-5 w-5 text-slate-400 group-hover:text-blue-400" />
                                </div>
                                <div className="min-w-0 flex-1">
                                    <p className="text-sm font-medium text-slate-200 truncate pr-2" title={file.file_name}>
                                        {file.file_name}
                                    </p>
                                    <div className="flex items-center gap-2 mt-0.5">
                                        <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500">
                                            {file.file_type.split('.').pop() || file.file_type}
                                        </span>
                                        <span className="text-[10px] text-slate-600">•</span>
                                        <span className="text-[10px] text-slate-500 font-medium">
                                            {formatDate(file.uploaded_at)}
                                        </span>
                                    </div>
                                </div>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => handleDelete(file.id)}
                                    disabled={deletingId === file.id}
                                    className="opacity-0 group-hover:opacity-100 h-8 w-8 text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-all"
                                >
                                    {deletingId === file.id ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                        <Trash2 className="h-4 w-4" />
                                    )}
                                </Button>
                            </div>
                        </div>
                    ))
                )}
            </div>

            <p className="text-[10px] text-slate-600 italic text-center mt-2 font-medium">
                Knowledge Library documents are persistent across all sessions.
            </p>
        </div>
    );
}
