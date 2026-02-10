"use client";

import { useState, useCallback, useRef } from "react";
import { Upload, FileText, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { FileUpload } from "@/types";
import { uploadFile } from "@/lib/api";

interface FileUploaderProps {
  sessionId: string;
  files: FileUpload[];
  onFilesChange: (files: FileUpload[]) => void;
  maxFiles?: number;
  accept?: string;
}

export function FileUploader({
  sessionId,
  files,
  onFilesChange,
  maxFiles = 5,
  accept = ".pdf,.txt,.doc,.docx",
}: FileUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    async (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);

      const droppedFiles = Array.from(e.dataTransfer.files);
      await uploadFiles(droppedFiles);
    },
    [files, sessionId]
  );

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      await uploadFiles(selectedFiles);
    }
  };

  const uploadFiles = async (newFiles: File[]) => {
    const remainingSlots = maxFiles - files.length;
    const filesToUpload = newFiles.slice(0, remainingSlots);

    for (let i = 0; i < filesToUpload.length; i++) {
      const file = filesToUpload[i];
      setUploading(i);

      try {
        const response = await uploadFile(sessionId, file);

        // Notify if it's a duplicate
        if (response.message.includes("Duplicate")) {
          alert(`Success: ${response.message}`);
        }

        const newFile: FileUpload = {
          name: file.name,
          size: file.size,
          type: file.type,
        };
        onFilesChange([...files, newFile]);
      } catch (error) {
        console.error("Upload failed:", error);
      } finally {
        setUploading(null);
      }
    }
  };

  const removeFile = (index: number) => {
    onFilesChange(files.filter((_, i) => i !== index));
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <Upload className="h-4 w-4 text-blue-400" />
        <span className="text-sm font-semibold text-slate-300">Session Documents</span>
      </div>

      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`border-2 border-dashed rounded-xl p-6 text-center transition-all duration-200 ${isDragging
          ? "border-blue-500 bg-blue-500/5 ring-4 ring-blue-500/10"
          : "border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-800/40"
          }`}
      >
        <Upload className="mx-auto h-8 w-8 text-slate-500 mb-2" />
        <p className="text-sm text-slate-400 mb-2 font-medium">
          Drag and drop files here, or click to select
        </p>
        <p className="text-xs text-slate-500">
          PDF, TXT, DOC, DOCX • Max {maxFiles} files
        </p>
        <input
          type="file"
          accept={accept}
          multiple
          onChange={handleFileSelect}
          className="hidden"
          id="file-upload"
          ref={fileInputRef}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="mt-4 border-slate-700 hover:bg-slate-800 text-slate-300"
          onClick={() => fileInputRef.current?.click()}
        >
          Select Files
        </Button>
      </div>

      {files.length > 0 && (
        <div className="space-y-2 pr-1">
          {files.map((file, index) => (
            <div
              key={index}
              className="group bg-slate-800/40 hover:bg-slate-800/80 border border-slate-700/50 rounded-xl p-3 transition-all duration-200"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-slate-700/50 rounded-lg group-hover:bg-blue-500/10 transition-colors">
                    <FileText className="h-5 w-5 text-slate-400 group-hover:text-blue-400" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-200">{file.name}</p>
                    <p className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mt-0.5">
                      {formatSize(file.size)} • {file.type.split('/').pop()}
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="opacity-0 group-hover:opacity-100 h-8 w-8 text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-all"
                  onClick={() => removeFile(index)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {uploading !== null && (
        <div className="flex items-center justify-center gap-2 text-xs text-slate-500 bg-slate-800/30 py-2 rounded-lg border border-slate-700/50">
          <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-400" />
          <span>Uploading file...</span>
        </div>
      )}
    </div>
  );
}
