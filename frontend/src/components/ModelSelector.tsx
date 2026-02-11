"use client";

import { useState, useEffect, useRef } from "react";
import { Settings, ChevronDown, Zap } from "lucide-react";
import { getCurrentModel, setCurrentModel, ModelInfo, ModelResponse } from "@/lib/api";

export function ModelSelector() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [currentModel, setCurrentModel] = useState<ModelInfo | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadModels();
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const loadModels = async () => {
    try {
      const data = await getCurrentModel();
      setCurrentModel(data.current);
      setModels(data.available);
    } catch (err) {
      console.error("Failed to load models:", err);
    }
  };

  const handleSelect = async (model: ModelInfo) => {
    try {
      await setCurrentModel(model.id);
      setCurrentModel(model);
      setIsOpen(false);
    } catch (err) {
      console.error("Failed to set model:", err);
    }
  };

  if (!currentModel) return null;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800/50 transition-all"
        title="Select LLM Model"
      >
        <Zap className="h-3.5 w-3.5" />
        <span className="hidden sm:inline font-medium">{currentModel.name}</span>
        <ChevronDown className={`h-3 w-3 transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <div className="absolute bottom-full right-0 mb-2 w-56 bg-slate-800/95 backdrop-blur-xl border border-slate-700/50 rounded-xl shadow-2xl overflow-hidden z-50">
          <div className="px-3 py-2 border-b border-slate-700/50">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">LLM Model</p>
          </div>
          {models.map((model) => (
            <button
              key={model.id}
              onClick={() => handleSelect(model)}
              className={`w-full px-4 py-2.5 text-left text-sm transition-all flex items-center gap-2 ${
                model.id === currentModel.id
                  ? "bg-blue-600/20 text-blue-400 border-l-2 border-blue-500"
                  : "text-slate-300 hover:bg-slate-700/50 hover:text-white"
              }`}
            >
              <Zap className="h-3.5 w-3.5 flex-shrink-0" />
              <span className="flex-1">{model.name}</span>
              {model.id === currentModel.id && (
                <span className="text-[10px] bg-blue-500/20 px-1.5 py-0.5 rounded text-blue-400">Active</span>
              )}
            </button>
          ))}
          <div className="px-3 py-2 border-t border-slate-700/50 bg-slate-900/50">
            <p className="text-[10px] text-slate-500">Click to switch models</p>
          </div>
        </div>
      )}
    </div>
  );
}
