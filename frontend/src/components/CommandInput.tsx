"use client";

import { useState, KeyboardEvent, useEffect, useCallback } from "react";
import { Send, Search, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

interface CommandInputProps {
  onSubmit: (command: string, researchEntities?: string[]) => void;
  isLoading: boolean;
}

interface ResearchChip {
  id: string;
  text: string;
  selected: boolean;
}

export function CommandInput({ onSubmit, isLoading }: CommandInputProps) {
  const [value, setValue] = useState("");
  const [researchMode, setResearchMode] = useState(false);
  const [chips, setChips] = useState<ResearchChip[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);

  // Extract potential entities from text (company names, people, etc.)
  const extractEntities = useCallback((text: string): string[] => {
    const entities: string[] = [];
    
    // Pattern 1: Company names (Corp, Inc, LLC, etc.)
    const companyPattern = /\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s*(?:Corp|Inc|LLC|Company|Co\.?|Ltd\.?))\b/g;
    let match;
    while ((match = companyPattern.exec(text)) !== null) {
      entities.push(match[1]);
    }
    
    // Pattern 2: Names with titles (Mr., Mrs., Dr., etc.)
    const namePattern = /\b(?:Mr\.?|Mrs\.?|Dr\.?|Ms\.?|Prof\.?)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\b/g;
    while ((match = namePattern.exec(text)) !== null) {
      entities.push(match[1]);
    }
    
    // Pattern 3: All-caps acronyms that might be organizations
    const acronymPattern = /\b([A-Z]{2,})\b/g;
    while ((match = acronymPattern.exec(text)) !== null) {
      // Filter out common words
      const commonWords = ['AI', 'PDF', 'CEO', 'CTO', 'CFO', 'VP', 'HR', 'IT'];
      if (!commonWords.includes(match[1])) {
        entities.push(match[1]);
      }
    }
    
    // Pattern 4: Capitalized names in specific contexts
    const capitalizedPattern = /(?:meeting with|interview with|from|at|about)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)/g;
    while ((match = capitalizedPattern.exec(text)) !== null) {
      entities.push(match[1]);
    }
    
    // Remove duplicates and return
    return [...new Set(entities)];
  }, []);

  // Update chips when value changes
  useEffect(() => {
    if (researchMode) {
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
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
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

  const toggleResearchMode = () => {
    setResearchMode(!researchMode);
    setShowDropdown(false);
    if (!researchMode) {
      // When enabling research mode, immediately extract entities
      const entities = extractEntities(value);
      setChips(entities.map((entity, index) => ({
        id: `chip-${index}`,
        text: entity,
        selected: true,
      })));
    } else {
      setChips([]);
    }
  };

  const handleResearchOption = (option: string) => {
    if (option === "everything") {
      // Select all detected entities
      setChips(prev => prev.map(chip => ({ ...chip, selected: true })));
    } else if (option === "custom") {
      // Keep current selection for user to customize
    }
    setShowDropdown(false);
  };

  const examples = [
    "Prepare me for tomorrow's meeting with Acme Corp using agenda.pdf",
    "Summarize this contract and flag all deadlines",
    "Extract tasks from last week's engineering meeting notes",
  ];

  return (
    <div className="w-full space-y-4">
      <div className="relative">
        <Input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={researchMode ? "What would you like to research?..." : "Ask anything or use context from files..."}
          disabled={isLoading}
          className="pr-24 h-14 text-lg bg-slate-900/50 border-slate-700 text-white placeholder:text-slate-500 focus:ring-blue-500/20"
        />
        
        {/* Research Button */}
        <div className="absolute right-14 top-1.5">
          <div className="relative">
            <Button
              onClick={() => setShowDropdown(!showDropdown)}
              onMouseEnter={() => !showDropdown && setShowDropdown(true)}
              disabled={isLoading}
              size="icon"
              className={`h-11 w-11 transition-all ${
                researchMode 
                  ? "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/20" 
                  : "bg-slate-700 hover:bg-slate-600 text-slate-300"
              }`}
              title="Toggle Research Mode"
            >
              <Search className="h-5 w-5" />
            </Button>
            
            {/* Dropdown Menu */}
            {showDropdown && (
              <div 
                className="absolute right-0 top-12 w-48 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 py-1"
                onMouseLeave={() => setShowDropdown(false)}
              >
                <button
                  onClick={toggleResearchMode}
                  className={`w-full px-4 py-2 text-left text-sm hover:bg-slate-700 transition-colors ${
                    researchMode ? "text-blue-400" : "text-slate-300"
                  }`}
                >
                  {researchMode ? "✓ Research Mode On" : "Enable Research Mode"}
                </button>
                {researchMode && (
                  <>
                    <div className="border-t border-slate-700 my-1" />
                    <button
                      onClick={() => handleResearchOption("everything")}
                      className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                    >
                      Research Everything
                    </button>
                    <button
                      onClick={() => handleResearchOption("custom")}
                      className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                    >
                      Custom Selection
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Send Button */}
        <Button
          onClick={handleSubmit}
          disabled={!value.trim() || isLoading}
          size="icon"
          className="absolute right-1.5 top-1.5 h-11 w-11 bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/20"
        >
          <Send className="h-5 w-5" />
        </Button>
      </div>

      {/* Research Mode Indicator & Chips */}
      {researchMode && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-600/20 border border-blue-500/30 rounded-full">
              <Search className="h-3 w-3 text-blue-400" />
              <span className="text-xs text-blue-400 font-medium">Research Mode Active</span>
            </div>
            {chips.length > 0 && (
              <span className="text-xs text-slate-500">
                Click chips to select/deselect entities to research
              </span>
            )}
          </div>
          
          {/* Entity Chips */}
          {chips.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {chips.map((chip) => (
                <button
                  key={chip.id}
                  onClick={() => toggleChip(chip.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs transition-all ${
                    chip.selected
                      ? "bg-blue-600 text-white border border-blue-500"
                      : "bg-slate-800 text-slate-400 border border-slate-700 hover:bg-slate-700"
                  }`}
                >
                  <Search className="h-3 w-3" />
                  {chip.text}
                  {chip.selected ? (
                    <span className="ml-1">✓</span>
                  ) : (
                    <X className="h-3 w-3" />
                  )}
                </button>
              ))}
            </div>
          )}
          
          {chips.length === 0 && value.length > 10 && (
            <p className="text-xs text-slate-500">
              Type company names, people, or topics to see research suggestions
            </p>
          )}
        </div>
      )}

      {/* Example Commands */}
      {!researchMode && (
        <div className="flex flex-wrap gap-2">
          <span className="text-sm text-slate-500">Try:</span>
          {examples.map((example, i) => (
            <button
              key={i}
              onClick={() => setValue(example)}
              className="px-3 py-1 rounded-full text-xs bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors border border-slate-700"
            >
              {example}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
