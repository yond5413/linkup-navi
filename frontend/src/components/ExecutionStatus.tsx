"use client";

import { ExecutionStatus } from "@/types";
import { CheckCircle2, Circle, Loader2, Sparkles } from "lucide-react";

interface ExecutionStatusProps {
  status: ExecutionStatus | null;
}

const steps = [
  "Planning",
  "Analyzing documents",
  "Extracting deadlines",
  "Extracting skills",
  "Researching entities",
  "Synthesizing information",
  "Generating response",
  "Complete",
];

export function ExecutionStatusDisplay({ status }: ExecutionStatusProps) {
  if (!status) return null;

  const currentStepIndex = steps.indexOf(status.current_step);
  const progress = Math.round(status.progress * 100);

  return (
    <div className="w-full space-y-4">
      {/* Progress Bar */}
      <div className="relative h-2 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
        {/* Shimmer effect */}
        <div className="absolute inset-y-0 w-20 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
      </div>

      {/* Progress Text */}
      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-400">
          {currentStepIndex >= 0 ? currentStepIndex + 1 : 0} of {steps.length - 1} steps
        </span>
        <span className="text-blue-400 font-mono">{progress}%</span>
      </div>

      {/* Current Step Highlight */}
      <div className="flex items-center gap-3 p-4 bg-slate-800/50 border border-slate-700 rounded-lg animate-in fade-in slide-in-from-bottom-2 duration-300">
        <div className="relative">
          {status.complete ? (
            <CheckCircle2 className="h-6 w-6 text-green-400" />
          ) : (
            <>
              <Loader2 className="h-6 w-6 text-blue-400 animate-spin" />
              <div className="absolute inset-0 bg-blue-400/20 blur-xl rounded-full animate-pulse" />
            </>
          )}
        </div>
        <div className="flex-1">
          <h4 className="text-white font-medium flex items-center gap-2">
            {status.current_step}
            {!status.complete && (
              <Sparkles className="h-4 w-4 text-purple-400 animate-pulse" />
            )}
          </h4>
          {status.reasoning && (
            <p className="text-slate-400 text-sm mt-1 animate-in fade-in duration-500">
              {status.reasoning}
            </p>
          )}
        </div>
      </div>

      {/* Steps List */}
      <div className="space-y-2 pt-2">
        {steps.slice(0, -1).map((step, index) => {
          const isCompleted = index < currentStepIndex;
          const isCurrent = index === currentStepIndex;

          return (
            <div
              key={step}
              className={`flex items-center gap-3 text-sm transition-colors duration-300 ${
                isCurrent
                  ? "text-blue-400"
                  : isCompleted
                  ? "text-slate-300"
                  : "text-slate-600"
              }`}
              style={{ animationDelay: `${index * 100}ms` }}
            >
              {isCompleted ? (
                <CheckCircle2 className="h-4 w-4 text-green-400 flex-shrink-0" />
              ) : isCurrent ? (
                <Circle className="h-4 w-4 text-blue-400 flex-shrink-0 animate-pulse" />
              ) : (
                <Circle className="h-4 w-4 flex-shrink-0" />
              )}
              <span className={isCurrent ? "font-medium" : ""}>{step}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
