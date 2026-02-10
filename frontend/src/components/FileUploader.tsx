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
        await uploadFile(sessionId, file);
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
    <div className="space-y-3">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
          isDragging
            ? "border-blue-500 bg-blue-50"
            : "border-slate-200 hover:border-slate-300"
        }`}
      >
        <Upload className="mx-auto h-8 w-8 text-slate-400 mb-2" />
        <p className="text-sm text-slate-600 mb-2">
          Drag and drop files here, or click to select
        </p>
        <p className="text-xs text-slate-400">
          PDF, TXT, DOC, DOCX up to {maxFiles} files
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
          className="mt-3"
          onClick={() => fileInputRef.current?.click()}
        >
          Select Files
        </Button>
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((file, index) => (
            <Card key={index} className="p-3">
              <CardContent className="flex items-center justify-between p-0">
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-slate-500" />
                  <div>
                    <p className="text-sm font-medium">{file.name}</p>
                    <p className="text-xs text-slate-500">
                      {formatSize(file.size)}
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => removeFile(index)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {uploading !== null && (
        <div className="flex items-center justify-center gap-2 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Uploading file...
        </div>
      )}
    </div>
  );
}
