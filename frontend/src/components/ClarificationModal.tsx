"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { ClarificationOption } from "@/types";
import { HelpCircle, ArrowRight } from "lucide-react";

interface ClarificationModalProps {
  message: string;
  options: ClarificationOption[];
  onSelect: (type: string) => void;
}

export function ClarificationModal({
  message,
  options,
  onSelect,
}: ClarificationModalProps) {
  return (
    <Card className="glass-card border-slate-700 overflow-hidden border-l-4 border-l-yellow-500">
      <CardHeader className="bg-slate-800/30 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <HelpCircle className="h-5 w-5 text-yellow-500" />
          <CardTitle className="text-slate-200">Help Us Understand</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pt-6 space-y-4">
        <p className="text-slate-300">{message}</p>
        
        <div className="space-y-2">
          {options.map((option) => (
            <Button
              key={option.type}
              variant="outline"
              className="w-full justify-between text-left h-auto py-4 px-4 border-slate-600 hover:border-blue-500 hover:bg-slate-800/50 group"
              onClick={() => onSelect(option.type)}
            >
              <div className="flex flex-col items-start">
                <span className="font-medium text-slate-200 group-hover:text-blue-400">
                  {option.label}
                </span>
                <span className="text-xs text-slate-500">
                  Confidence: {Math.round(option.confidence * 100)}%
                </span>
              </div>
              <ArrowRight className="h-4 w-4 text-slate-500 group-hover:text-blue-400" />
            </Button>
          ))}
        </div>
        
        <p className="text-xs text-slate-500 italic">
          Select the option that best matches your request
        </p>
      </CardContent>
    </Card>
  );
}
