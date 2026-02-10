"use client";

import { useState, KeyboardEvent, useEffect, useCallback, useRef } from "react";
import { Send, Search, X, PlusCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Textarea";

interface CommandInputProps {
  onSubmit: (command: string, researchEntities?: string[]) => void;
  isLoading: boolean;
  placeholder?: string;
}

interface ResearchChip {
  id: string;
  text: string;
  selected: boolean;
}

export function CommandInput({ onSubmit, isLoading, placeholder }: CommandInputProps) {
  const [value, setValue] = useState("");
  const [researchMode, setResearchMode] = useState(false);
  const [chips, setChips] = useState<ResearchChip[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [value]);

  // Extract potential entities from text
  const extractEntities = useCallback((text: string): string[] => {
    const entities: string[] = [];
    const companyPattern = /\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s*(?:Corp|Inc|LLC|Company|Co\.?|Ltd\.?))\b/g;
    let match;
    while ((match = companyPattern.exec(text)) !== null) {
      entities.push(match[1]);
    }
    const namePattern = /\b(?:Mr\.?|Mrs\.?|Dr\.?|Ms\.?|Prof\.?)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\b/g;
    while ((match = namePattern.exec(text)) !== null) {
      entities.push(match[1]);
    }
    const acronymPattern = /\b([A-Z]{2,})\b/g;
    while ((match = acronymPattern.exec(text)) !== null) {
      const commonWords = ['AI', 'PDF', 'CEO', 'CTO', 'CFO', 'VP', 'HR', 'IT'];
      if (!commonWords.includes(match[1])) {
        entities.push(match[1]);
      }
    }
    const capitalizedPattern = /(?:meeting with|interview with|from|at|about)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)/g;
    while ((match = capitalizedPattern.exec(text)) !== null) {
      entities.push(match[1]);
    }
    return [...new Set(entities)];
  }, []);

  useEffect(() => {
    if (researchMode && value.length > 5) {
      const entities = extractEntities(value);
      const newChips = entities.map((entity, index) => ({
        id: `chip-${index}`,
        text: entity,
        selected: true,
      }));
      setChips(newChips);
    }
  }, [value, researchMode, extractEntities]);

  const handleSubmit = () => {
    if (value.trim() && !isLoading) {
      const selectedEntities = chips
        .filter(chip => chip.selected)
        .map(chip => chip.text);
      onSubmit(value.trim(), selectedEntities.length > 0 ? selectedEntities : undefined);
      setValue("");
      setChips([]);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const toggleChip = (chipId: string) => {
    setChips(prev => prev.map(chip =>
      chip.id === chipId ? { ...chip, selected: !chip.selected } : chip
    ));
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4">
      <div className="relative group transition-all duration-300">
        <div className="absolute -top-12 left-0 right-0 flex items-center justify-between pb-2 bg-gradient-to-t from-[#0f172a] to-transparent h-12 pointer-events-none opacity-0 group-focus-within:opacity-100 transition-opacity">
          {researchMode && (
            <div className="flex items-center gap-2 px-3 py-1 bg-blue-600/20 border border-blue-500/30 rounded-full ml-2">
              <Search className="h-3 w-3 text-blue-400" />
              <span className="text-[10px] text-blue-400 font-bold uppercase tracking-wider">Research Active</span>
            </div>
          )}
        </div>

        <div className="relative bg-slate-900/60 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl focus-within:border-blue-500/50 focus-within:ring-4 focus-within:ring-blue-500/10 transition-all p-2">
          <div className="flex items-end gap-2">

            <Textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder || (researchMode ? "What entity should I research?..." : "Type a command or ask a question...")}
              className="flex-1 min-h-[44px] max-h-[200px] py-3 bg-transparent border-0 focus-visible:ring-0 text-slate-200 placeholder:text-slate-500 resize-none font-sans text-[15px] leading-relaxed"
            />

            <div className="flex items-center gap-1.5 pb-0.5 pr-0.5">
              <Button
                onClick={() => setResearchMode(!researchMode)}
                size="icon"
                className={`h-9 w-9 rounded-xl transition-all ${researchMode
                  ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20"
                  : "bg-slate-800/50 text-slate-400 hover:bg-slate-700"
                  }`}
                title="Toggle Research Mode"
              >
                <Search className="h-4 w-4" />
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={!value.trim() || isLoading}
                size="icon"
                className="h-9 w-9 bg-blue-500 hover:bg-blue-400 text-white shadow-lg shadow-blue-500/20 rounded-xl disabled:bg-slate-800 disabled:text-slate-600 appearance-none"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Chips Section - Persistent when research mode is on */}
          {researchMode && chips.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5 px-2 pb-1 border-t border-slate-800/50 pt-2 animate-in fade-in slide-in-from-top-1">
              {chips.map((chip) => (
                <button
                  key={chip.id}
                  onClick={() => toggleChip(chip.id)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs transition-all ${chip.selected
                    ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                    : "bg-slate-800 text-slate-500 border border-transparent hover:border-slate-700"
                    }`}
                >
                  {chip.text}
                  {chip.selected && <span className="text-[8px] font-bold">✓</span>}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="mt-3 flex justify-center">
          <p className="text-[10px] text-slate-500 font-medium tracking-wide">
            SHIFT + ENTER for new line • ESC to clear
          </p>
        </div>
      </div>
    </div>
  );
}
