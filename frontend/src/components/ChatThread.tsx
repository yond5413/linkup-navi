"use client";

import { useEffect, useRef } from "react";
import { User, Bot, Sparkles } from "lucide-react";
import { ExecutionStatusDisplay } from "./ExecutionStatus";
import { ClarificationModal } from "./ClarificationModal";
import { ExecutionStatus, ClarificationOption } from "@/types";

interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    type: "text" | "status" | "clarification";
    status?: ExecutionStatus | null;
    clarification?: {
        message: string;
        options: ClarificationOption[];
    };
}

interface ChatThreadProps {
    messages: Message[];
    isLoading: boolean;
    onClarify: (type: string) => void;
}

export function ChatThread({ messages, isLoading, onClarify }: ChatThreadProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, isLoading]);

    return (
        <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto px-4 py-8 space-y-8 scroll-smooth"
        >
            {messages.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-50">
                    <div className="p-4 bg-slate-800/50 rounded-2xl border border-slate-700/50">
                        <Sparkles className="h-8 w-8 text-blue-400" />
                    </div>
                    <div className="space-y-1">
                        <h3 className="text-lg font-semibold text-slate-200">How can I help you today?</h3>
                        <p className="text-sm text-slate-500 max-w-xs">
                            Upload documents or ask me to research topics to manifest a briefing in your workspace.
                        </p>
                    </div>
                </div>
            )}

            {messages.map((message) => (
                <div
                    key={message.id}
                    className={`flex gap-4 animate-in fade-in slide-in-from-bottom-2 duration-300 ${message.role === "user" ? "justify-end" : "justify-start"
                        }`}
                >
                    {message.role === "assistant" && (
                        <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-600/20">
                            <Bot className="h-5 w-5 text-white" />
                        </div>
                    )}

                    <div className={`max-w-[85%] space-y-2 ${message.role === "user" ? "items-end" : "items-start"}`}>
                        {message.type === "text" && (
                            <div className={`px-4 py-3 rounded-2xl text-[15px] leading-relaxed ${message.role === "user"
                                    ? "bg-blue-600 text-white shadow-xl shadow-blue-600/10"
                                    : "bg-slate-800 text-slate-200 border border-slate-700/50"
                                }`}>
                                {message.content}
                            </div>
                        )}

                        {message.type === "status" && message.status && (
                            <div className="w-full min-w-[300px] lg:min-w-[400px] bg-slate-800/50 border border-slate-700/50 rounded-2xl p-4">
                                <ExecutionStatusDisplay status={message.status} />
                            </div>
                        )}

                        {message.type === "clarification" && message.clarification && (
                            <div className="w-full min-w-[300px] lg:min-w-[400px]">
                                <ClarificationModal
                                    message={message.clarification.message}
                                    options={message.clarification.options}
                                    onSelect={onClarify}
                                />
                            </div>
                        )}
                    </div>

                    {message.role === "user" && (
                        <div className="h-8 w-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0 border border-slate-600">
                            <User className="h-5 w-5 text-slate-300" />
                        </div>
                    )}
                </div>
            ))}

            {isLoading && messages.length > 0 && messages[messages.length - 1].role === "user" && (
                <div className="flex gap-4 animate-pulse">
                    <div className="h-8 w-8 rounded-full bg-slate-800 flex items-center justify-center flex-shrink-0 opacity-50">
                        <Bot className="h-5 w-5 text-slate-500" />
                    </div>
                    <div className="space-y-2 pt-2">
                        <div className="h-2 w-24 bg-slate-800 rounded-full" />
                        <div className="h-2 w-32 bg-slate-800 rounded-full" />
                    </div>
                </div>
            )}
        </div>
    );
}
