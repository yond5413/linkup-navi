"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { BriefingOutput, DynamicOutput, ResponseSection, ResearchMetadata, ResearchSource } from "@/types";
import {
  FileText,
  AlertTriangle,
  LinkIcon,
  CheckSquare,
  Clock,
  Sparkles,
  ExternalLink,
  Search,
} from "lucide-react";

interface OutputPanelProps {
  output: BriefingOutput | DynamicOutput | null;
  isLoading: boolean;
}

// Helper to determine if output is the new DynamicOutput type
function isDynamicOutput(output: BriefingOutput | DynamicOutput): output is DynamicOutput {
  return "sections" in output && "query_type" in output;
}

export function OutputPanel({ output, isLoading }: OutputPanelProps) {
  const [activeSection, setActiveSection] = useState<string | null>(null);

  if (isLoading) {
    return (
      <Card className="h-full flex items-center justify-center min-h-[400px] glass-card border-slate-700">
        <CardContent className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400 mx-auto mb-4" />
          <p className="text-slate-400">Synthesizing intelligence...</p>
        </CardContent>
      </Card>
    );
  }

  if (!output) {
    return (
      <Card className="h-full flex items-center justify-center min-h-[400px] glass-card border-slate-700">
        <CardContent className="text-center">
          <FileText className="mx-auto h-12 w-12 text-slate-600 mb-3" />
          <p className="text-slate-400">
            Submit a command to manifest the briefing
          </p>
        </CardContent>
      </Card>
    );
  }

  // Render legacy BriefingOutput structure
  if (!isDynamicOutput(output)) {
    return <LegacyOutputPanel output={output} />;
  }

  // Render new DynamicOutput structure
  const { query_type_label, sections, research_metadata } = output;
  
  // Set initial active section if not set
  if (!activeSection && sections.length > 0) {
    setActiveSection(sections[0].id);
  }

  const currentSection = sections.find(s => s.id === activeSection) || sections[0];

  return (
    <Card className="h-full glass-card border-slate-700 animate-in">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-blue-400" />
            <span className="text-sm font-medium text-blue-400">
              {query_type_label}
            </span>
            {research_metadata && (
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                research_metadata.auto_researched 
                  ? "bg-slate-700 text-slate-400" 
                  : "bg-blue-600/30 text-blue-400 border border-blue-500/30"
              }`}>
                <Search className="h-3 w-3 inline mr-1" />
                {research_metadata.auto_researched ? "Auto-researched" : "Research requested"}
              </span>
            )}
          </div>
        </div>
        
        {/* Dynamic section tabs */}
        <div className="flex gap-1 border-b border-slate-700 overflow-x-auto">
          {sections.map((section) => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              className={`flex items-center gap-2 px-4 py-2 text-sm border-b-2 transition-all whitespace-nowrap ${
                activeSection === section.id
                  ? "border-blue-400 text-blue-400"
                  : "border-transparent text-slate-400 hover:text-slate-300"
              }`}
            >
              {getSectionIcon(section.id)}
              {section.title}
            </button>
          ))}
        </div>
      </CardHeader>
      
      <CardContent className="overflow-y-auto max-h-[600px]">
        {currentSection && (
          <div className="prose prose-sm max-w-none prose-invert">
            <div 
              className="whitespace-pre-wrap text-slate-300 leading-relaxed"
              dangerouslySetInnerHTML={{ 
                __html: formatContent(currentSection.content) 
              }}
            />
          </div>
        )}
        
        {/* Research Sources Section */}
        {research_metadata && research_metadata.sources.length > 0 && (
          <div className="mt-8 pt-6 border-t border-slate-700">
            <div className="flex items-center gap-2 mb-4">
              <LinkIcon className="h-4 w-4 text-blue-400" />
              <h4 className="text-sm font-medium text-slate-200">
                Research Sources
                {research_metadata.entities.length > 0 && (
                  <span className="text-slate-500 ml-2">
                    ({research_metadata.entities.join(", ")})
                  </span>
                )}
              </h4>
            </div>
            <div className="space-y-3">
              {research_metadata.sources.map((source, index) => (
                <a
                  key={index}
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-start gap-3 p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition-colors group"
                >
                  {source.favicon ? (
                    <img 
                      src={source.favicon} 
                      alt="" 
                      className="h-4 w-4 mt-0.5 opacity-60 group-hover:opacity-100"
                    />
                  ) : (
                    <LinkIcon className="h-4 w-4 mt-0.5 text-slate-500" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-blue-400 group-hover:text-blue-300 truncate">
                        {source.title}
                      </span>
                      <ExternalLink className="h-3 w-3 text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                      {source.snippet}
                    </p>
                    <span className="text-xs text-slate-600 mt-1 block truncate">
                      {source.url}
                    </span>
                  </div>
                </a>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
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
    background_context: <LinkIcon className="h-4 w-4" />,
    research: <LinkIcon className="h-4 w-4" />,
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
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-white">$1</strong>')
    // Italic text
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Bullet points
    .replace(/^- (.+)$/gm, '<li class="ml-4">$1</li>')
    // Headers
    .replace(/^#{1,3} (.+)$/gm, '<h3 class="text-lg font-semibold text-white mt-4 mb-2">$1</h3>');
}

// Legacy output panel for backward compatibility
function LegacyOutputPanel({ output }: { output: BriefingOutput }) {
  const [activeTab, setActiveTab] = useState<"summary" | "deadlines" | "risks" | "research" | "actions">("summary");

  const tabs = [
    { id: "summary" as const, label: "Summary", icon: <FileText className="h-4 w-4" /> },
    { id: "deadlines" as const, label: "Deadlines", icon: <Clock className="h-4 w-4" /> },
    { id: "risks" as const, label: "Risks", icon: <AlertTriangle className="h-4 w-4" /> },
    { id: "research" as const, label: "Research", icon: <LinkIcon className="h-4 w-4" /> },
    { id: "actions" as const, label: "Actions", icon: <CheckSquare className="h-4 w-4" /> },
  ];

  return (
    <Card className="h-full glass-card border-slate-700">
      <CardHeader className="pb-3">
        <div className="flex gap-1 border-b border-slate-700">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 text-sm border-b-2 transition-all ${
                activeTab === tab.id
                  ? "border-blue-400 text-blue-400"
                  : "border-transparent text-slate-400 hover:text-slate-300"
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {activeTab === "summary" && (
          <div className="prose prose-sm max-w-none">
            <p className="whitespace-pre-wrap">{output.summary}</p>
          </div>
        )}

        {activeTab === "deadlines" && (
          <ul className="space-y-2">
            {output.deadlines.length > 0 ? (
              output.deadlines.map((deadline, i) => (
                <li key={i} className="flex items-start gap-2">
                  <Clock className="h-4 w-4 text-orange-500 mt-0.5" />
                  <span>{deadline}</span>
                </li>
              ))
            ) : (
              <p className="text-slate-500">No deadlines found</p>
            )}
          </ul>
        )}

        {activeTab === "risks" && (
          <ul className="space-y-2">
            {output.risks.length > 0 ? (
              output.risks.map((risk, i) => (
                <li key={i} className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5" />
                  <span>{risk}</span>
                </li>
              ))
            ) : (
              <p className="text-slate-500">No risks identified</p>
            )}
          </ul>
        )}

        {activeTab === "research" && (
          <div>
            {output.research ? (
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium">{output.research.entity}</h4>
                </div>
                <ul className="space-y-2">
                  {output.research.snippets.map((snippet, i) => (
                    <li key={i} className="text-sm text-slate-600">
                      {snippet}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-slate-500">No research data available</p>
            )}
          </div>
        )}

        {activeTab === "actions" && (
          <ul className="space-y-2">
            {output.actions && output.actions.length > 0 ? (
              output.actions.map((action, i) => (
                <li key={i} className="flex items-start gap-2">
                  <CheckSquare className="h-4 w-4 text-green-500 mt-0.5" />
                  <span>{action}</span>
                </li>
              ))
            ) : (
              <p className="text-slate-500">No action items identified</p>
            )}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
