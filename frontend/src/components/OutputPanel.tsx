"use client";

import { useState, useMemo } from "react";
import { BriefingOutput, DynamicOutput, FileUpload } from "@/types";
import {
  FileText,
  AlertTriangle,
  LinkIcon,
  CheckSquare,
  Clock,
  Sparkles,
  ExternalLink,
  Search,
  Copy,
  ChevronRight,
  RefreshCw,
  Upload,
  Library,
} from "lucide-react";
import { Button } from "./ui/Button";
import { FileUploader } from "./FileUploader";
import { KnowledgeLibrary } from "./KnowledgeLibrary";

interface OutputPanelProps {
  output: BriefingOutput | DynamicOutput | null;
  isLoading: boolean;
  onRefine?: (prompt: string) => void;
  files: FileUpload[];
  setFiles: (files: FileUpload[]) => void;
  sessionId: string;
}

// Helper to determine if output is the new DynamicOutput type
function isDynamicOutput(output: BriefingOutput | DynamicOutput): output is DynamicOutput {
  return output && "sections" in output && "query_type" in output;
}

export function OutputPanel({ output, isLoading, onRefine, files, setFiles, sessionId }: OutputPanelProps) {
  const [activeSection, setActiveSection] = useState<string | null>(null);

  const sections = useMemo(() => {
    const reportSections = (output ? (isDynamicOutput(output) ? output.sections : [
      { id: "summary", title: "Executive Summary", content: (output as BriefingOutput).summary },
      { id: "deadlines", title: "Key Deadlines", content: (output as BriefingOutput).deadlines.join("\n") },
      { id: "risks", title: "Identified Risks", content: (output as BriefingOutput).risks.join("\n") },
      { id: "actions", title: "Action Items", content: ((output as BriefingOutput).actions || []).join("\n") },
    ]) : []).filter(s => s.content && s.content.length > 0);

    const resourceSections = [
      { id: "uploads", title: "Session Files", icon: <Upload className="h-4 w-4" /> },
      { id: "library", title: "Knowledge Library", icon: <Library className="h-4 w-4" /> },
    ];

    return { report: reportSections, resources: resourceSections };
  }, [output]);

  // Combined flat list for easy lookups
  const allSections = [...sections.report, ...sections.resources];

  if (!activeSection && allSections.length > 0) {
    if (sections.report.length > 0) {
      setActiveSection(sections.report[0].id);
    } else {
      setActiveSection("uploads");
    }
  }

  const currentSection = allSections.find(s => s.id === activeSection) || allSections[0];

  const handleCopy = () => {
    if (!currentSection || !("content" in currentSection)) return;
    navigator.clipboard.writeText((currentSection as any).content);
  };

  const isReportSection = sections.report.some(s => s.id === activeSection);

  if (!output && !isLoading && activeSection !== "uploads" && activeSection !== "library") {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center space-y-6 opacity-30 grayscale hover:grayscale-0 hover:opacity-100 transition-all duration-700">
        <div className="relative">
          <div className="absolute inset-0 bg-blue-500/10 blur-3xl rounded-full" />
          <FileText className="h-24 w-24 text-slate-500 relative" />
        </div>
        <div className="space-y-4">
          <h3 className="text-xl font-bold text-slate-400">Intelligence Workspace</h3>
          <p className="text-sm text-slate-600 max-w-xs mx-auto">
            Briefings, research, and analysis will manifest here. You can also manage your files.
          </p>
          <div className="flex gap-3 justify-center">
            <Button variant="outline" size="sm" onClick={() => setActiveSection("uploads")} className="text-xs uppercase tracking-widest font-bold">Manage Files</Button>
            <Button variant="outline" size="sm" onClick={() => setActiveSection("library")} className="text-xs uppercase tracking-widest font-bold">Browse Library</Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-slate-900/40 border border-slate-800 rounded-3xl overflow-hidden shadow-2xl animate-in fade-in duration-700 relative">
      {/* Document Header */}
      <header className="px-6 py-5 border-b border-slate-800 bg-slate-900/60 backdrop-blur-md flex items-center justify-between z-10 font-sans">
        <div className="flex items-center gap-3 font-sans">
          <div className={`p-2 rounded-xl border transition-all ${isReportSection ? 'bg-blue-600/10 border-blue-500/20' : 'bg-slate-800 border-slate-700'}`}>
            {isReportSection ? <Sparkles className="h-5 w-5 text-blue-400" /> : (activeSection === "uploads" ? <Upload className="h-5 w-5 text-slate-400" /> : <Library className="h-5 w-5 text-slate-400" />)}
          </div>
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              {activeSection === "uploads" ? "Session Files" : (activeSection === "library" ? "Knowledge Library" : (isDynamicOutput(output!) ? output.query_type_label : "Intelligence Briefing"))}
            </h2>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[10px] text-slate-500 uppercase font-bold tracking-[0.1em]">{isReportSection ? 'Verified Report' : 'Resources'}</span>
              <div className="h-1 w-1 rounded-full bg-slate-700" />
              <span className="text-[10px] text-slate-500 uppercase font-bold tracking-[0.1em]">
                {new Date().toLocaleDateString("en-US", { month: "short", day: "numeric" })}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isReportSection && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopy}
                className="h-8 rounded-lg bg-slate-800/50 border-slate-700 hover:bg-slate-700 text-xs gap-2"
              >
                <Copy className="h-3.5 w-3.5" />
                Copy
              </Button>
              {onRefine && (
                <Button
                  size="sm"
                  onClick={() => onRefine("Refine this section...")}
                  className="h-8 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs gap-2 shadow-lg shadow-blue-600/20"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Refine
                </Button>
              )}
            </>
          )}
        </div>
      </header>

      {/* Document Content */}
      <div className="flex-1 flex overflow-hidden font-sans">
        {/* Section Nav */}
        <aside className="w-60 border-r border-slate-800/50 bg-slate-900/20 p-4 flex flex-col overflow-hidden flex-shrink-0">
          <div className="space-y-6 flex-1 overflow-y-auto pr-2">
            {sections.report.length > 0 && (
              <div className="space-y-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] px-3 mb-2 block">Briefing Sections</span>
                {sections.report.map((section) => (
                  <SectionButton
                    key={section.id}
                    id={section.id}
                    title={section.title}
                    activeSection={activeSection}
                    onClick={setActiveSection}
                    icon={getSectionIcon(section.id)}
                  />
                ))}
              </div>
            )}

            <div className="space-y-1">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] px-3 mb-2 block">Resources</span>
              {sections.resources.map((section) => (
                <SectionButton
                  key={section.id}
                  id={section.id}
                  title={section.title}
                  activeSection={activeSection}
                  onClick={setActiveSection}
                  icon={section.icon}
                />
              ))}
            </div>
          </div>
        </aside>

        {/* Section Content */}
        <main className="flex-1 overflow-y-auto flex flex-col bg-slate-900/10">
          {activeSection === "uploads" ? (
            <div className="p-8 h-full">
              <div className="max-w-3xl mx-auto space-y-8 animate-in fade-in duration-500">
                <div className="space-y-2 text-center pb-8 border-b border-slate-800/50">
                  <h3 className="text-2xl font-bold text-white tracking-tight">Session Files</h3>
                  <p className="text-slate-500 text-sm">Upload documents to provide context for this session.</p>
                </div>
                <FileUploader
                  sessionId={sessionId || ""}
                  files={files}
                  onFilesChange={setFiles}
                />
              </div>
            </div>
          ) : activeSection === "library" ? (
            <div className="h-full overflow-hidden flex flex-col">
              <KnowledgeLibrary />
            </div>
          ) : currentSection && "content" in currentSection ? (
            <div className="p-8">
              <div className="max-w-3xl mx-auto space-y-8 animate-in fade-in slide-in-from-right-4 duration-500">
                <div className="space-y-2">
                  <h3 className="text-2xl font-bold text-white tracking-tight">{currentSection.title}</h3>
                  <div className="h-1 w-12 bg-blue-600 rounded-full" />
                </div>

                <div className="prose prose-invert prose-blue max-w-none">
                  <div
                    className="whitespace-pre-wrap text-slate-300 leading-relaxed text-[16px]"
                    dangerouslySetInnerHTML={{
                      __html: formatContent((currentSection as any).content)
                    }}
                  />
                </div>

                {isDynamicOutput(output!) && output.research_metadata && output.research_metadata.sources.length > 0 && activeSection === "research" && (
                  <ResearchSources sources={output.research_metadata.sources} />
                )}
              </div>
            </div>
          ) : null}
        </main>
      </div>
    </div>
  );
}

function SectionButton({ id, title, activeSection, onClick, icon }: any) {
  return (
    <button
      onClick={() => onClick(id)}
      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left text-sm transition-all group ${activeSection === id
          ? "bg-blue-600/10 text-blue-400 border border-blue-500/20"
          : "text-slate-500 hover:text-slate-300 hover:bg-slate-800/50"
        }`}
    >
      <div className={`p-1 rounded-md transition-colors ${activeSection === id ? "bg-blue-600/20 text-blue-400" : "bg-slate-800 text-slate-600 group-hover:text-slate-400"
        }`}>
        {icon}
      </div>
      <span className="flex-1 truncate font-medium">{title}</span>
      {activeSection === id && (
        <ChevronRight className="h-3 w-3 opacity-50" />
      )}
    </button>
  );
}

function ResearchSources({ sources }: { sources: any[] }) {
  return (
    <div className="mt-12 space-y-6 px-4 pb-12">
      <div className="flex items-center gap-2">
        <div className="h-px flex-1 bg-slate-800" />
        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest whitespace-nowrap px-4">Sources Citations</span>
        <div className="h-px flex-1 bg-slate-800" />
      </div>
      <div className="grid gap-4">
        {sources.map((source, index) => (
          <a
            key={index}
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group p-4 bg-slate-800/30 border border-slate-700/30 rounded-2xl hover:bg-slate-800/50 hover:border-blue-500/30 transition-all flex items-start gap-4"
          >
            <div className="h-10 w-10 rounded-xl bg-slate-900/50 border border-slate-700 flex items-center justify-center flex-shrink-0 group-hover:bg-blue-600/10 group-hover:border-blue-500/30 transition-all">
              {source.favicon ? (
                <img src={source.favicon} alt="" className="h-5 w-5 opacity-70 group-hover:opacity-100" />
              ) : (
                <LinkIcon className="h-5 w-5 text-slate-500 group-hover:text-blue-400" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-semibold text-slate-200 group-hover:text-white transition-colors truncate">{source.title}</h4>
              <p className="text-xs text-slate-500 mt-1 line-clamp-2 leading-relaxed">{source.snippet}</p>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-[10px] text-blue-500/80 font-mono truncate">{new URL(source.url).hostname}</span>
                <ExternalLink className="h-3 w-3 text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

// Helper to get icon based on section name
function getSectionIcon(sectionId: string): React.ReactNode {
  const iconMap: Record<string, React.ReactNode> = {
    executive_summary: <FileText className="h-4 w-4" />,
    summary: <FileText className="h-4 w-4" />,
    key_strengths: <Sparkles className="h-4 w-4" />,
    experience_analysis: <FileText className="h-4 w-4" />,
    skills_assessment: <CheckSquare className="h-4 w-4" />,
    potential_concerns: <AlertTriangle className="h-4 w-4" />,
    overall_verdict: <CheckSquare className="h-4 w-4" />,
    agenda_summary: <FileText className="h-4 w-4" />,
    key_deadlines: <Clock className="h-4 w-4" />,
    deadlines: <Clock className="h-4 w-4" />,
    risks_and_considerations: <AlertTriangle className="h-4 w-4" />,
    risks: <AlertTriangle className="h-4 w-4" />,
    background_context: <Search className="h-4 w-4" />,
    research: <Search className="h-4 w-4" />,
    actionable_briefing: <CheckSquare className="h-4 w-4" />,
    actions: <CheckSquare className="h-4 w-4" />,
    key_terms: <FileText className="h-4 w-4" />,
    obligations: <CheckSquare className="h-4 w-4" />,
    risk_factors: <AlertTriangle className="h-4 w-4" />,
    recommendations: <Sparkles className="h-4 w-4" />,
  };

  return iconMap[sectionId] || <FileText className="h-4 w-4" />;
}

// Helper to format content (basic markdown-like formatting)
function formatContent(content: string): string {
  if (!content) return "";

  return content
    // Bold text
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>')
    // Italic text
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Bullet points
    .replace(/^- (.+)$/gm, '<li class="ml-4 pl-2 mb-1">$1</li>')
    // Headers
    .replace(/^#{1,3} (.+)$/gm, '<h3 class="text-xl font-bold text-white mt-8 mb-4 tracking-tight">$1</h3>');
}
