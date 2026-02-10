"use client";

import { useState, useEffect } from "react";
import { Database, Search, Clock, AlertTriangle, ChevronDown, ChevronUp, RefreshCw } from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { AdminSidebar } from "@/components/AdminSidebar";
import { getMemoryStats, getRecentChunks, searchMemory, MemoryStats, MemoryChunk, MemorySearchResult } from "@/lib/api";

export default function AdminMemoryPage() {
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [recentChunks, setRecentChunks] = useState<MemoryChunk[]>([]);
  const [recentLimit, setRecentLimit] = useState(10);
  const [query, setQuery] = useState("");
  const [searchK, setSearchK] = useState(5);
  const [searchResults, setSearchResults] = useState<MemorySearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [expandedChunks, setExpandedChunks] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, []);

  useEffect(() => {
    loadRecentChunks();
  }, [recentLimit]);

  const loadStats = async () => {
    try {
      const statsData = await getMemoryStats();
      setStats(statsData);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load stats");
      setLoading(false);
    }
  };

  const loadRecentChunks = async () => {
    try {
      const chunks = await getRecentChunks(recentLimit);
      setRecentChunks(chunks);
    } catch (err) {
      console.error("Failed to load recent chunks:", err);
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const results = await searchMemory(query, searchK);
      setSearchResults(results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setSearching(false);
    }
  };

  const toggleChunkExpand = (index: number) => {
    const newExpanded = new Set(expandedChunks);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedChunks(newExpanded);
  };

  const distanceToSimilarity = (distance: number): number => {
    const maxDist = 200;
    const similarity = Math.max(0, 100 * Math.exp(-distance / 100));
    return Math.round(similarity);
  };

  const getSimilarityColor = (similarity: number): string => {
    if (similarity >= 70) return "text-emerald-400 bg-emerald-500/20";
    if (similarity >= 40) return "text-amber-400 bg-amber-500/20";
    return "text-red-400 bg-red-500/20";
  };

  const getSimilarityLabel = (similarity: number): string => {
    if (similarity >= 70) return "High";
    if (similarity >= 40) return "Medium";
    return "Low";
  };

  if (loading) {
    return (
      <div className="min-h-screen">
        <div className="pr-16 min-h-screen p-8">
          <div className="glass-card rounded-xl p-8 animate-pulse max-w-6xl">
            <div className="h-6 bg-white/10 rounded w-1/4 mb-4"></div>
            <div className="space-y-3">
              <div className="h-4 bg-white/10 rounded w-full"></div>
              <div className="h-4 bg-white/10 rounded w-5/6"></div>
              <div className="h-4 bg-white/10 rounded w-4/6"></div>
            </div>
          </div>
        </div>
        <AdminSidebar />
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="min-h-screen">
        <div className="pr-16 min-h-screen p-8">
          <div className="glass-card rounded-xl p-8 text-center max-w-6xl mx-auto">
            <AlertTriangle className="h-12 w-12 text-amber-400 mx-auto mb-4" />
            <p className="text-red-400">Error: {error}</p>
            <p className="text-slate-400 mt-2">Make sure the backend server is running on port 8000</p>
          </div>
        </div>
        <AdminSidebar />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="pr-16 min-h-screen p-8">
        <div className="max-w-6xl mx-auto space-y-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">FAISS Vector Memory</h1>
              <p className="text-slate-400 text-sm mt-1">
                Semantic memory visualization for the agent&apos;s long-term memory
              </p>
            </div>
            <Button variant="ghost" size="sm" onClick={loadStats}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>

          <section>
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Database className="h-5 w-5 text-blue-400" />
              Memory Statistics
            </h2>
            <div className="grid grid-cols-3 gap-4">
              <Card className="bg-slate-800/50 border-slate-700/50">
                <CardContent className="pt-6">
                  <div className="text-sm text-slate-400 mb-1">Total Vectors</div>
                  <div className="text-3xl font-bold text-blue-400">
                    {stats?.total_vectors ?? 0}
                  </div>
                  <div className="text-xs text-slate-500 mt-2">
                    Chunks embedded in FAISS
                  </div>
                </CardContent>
              </Card>
              <Card className="bg-slate-800/50 border-slate-700/50">
                <CardContent className="pt-6">
                  <div className="text-sm text-slate-400 mb-1">Index Name</div>
                  <div className="text-lg font-mono text-slate-200 mt-1">
                    {stats?.index_name ?? "N/A"}
                  </div>
                  <div className="text-xs text-slate-500 mt-2">
                    FAISS index identifier
                  </div>
                </CardContent>
              </Card>
              <Card className="bg-slate-800/50 border-slate-700/50">
                <CardContent className="pt-6">
                  <div className="text-sm text-slate-400 mb-1">Cohere Integration</div>
                  <div className="mt-1">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      stats?.cohere_configured 
                        ? "bg-emerald-500/20 text-emerald-400" 
                        : "bg-red-500/20 text-red-400"
                    }`}>
                      {stats?.cohere_configured ? "Connected" : "Not Configured"}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 mt-2">
                    embed-english-v3.0 model
                  </div>
                </CardContent>
              </Card>
            </div>
          </section>

          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Clock className="h-5 w-5 text-purple-400" />
                Recent Memory Chunks
              </h2>
              <div className="flex items-center gap-2">
                <label className="text-sm text-slate-400">Show last</label>
                <select
                  value={recentLimit}
                  onChange={(e) => setRecentLimit(Number(e.target.value))}
                  className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm"
                >
                  {[5, 10, 15, 20, 30, 50].map(n => (
                    <option key={n} value={n}>{n}</option>
                  ))}
                </select>
              </div>
            </div>
            
            {recentChunks.length === 0 ? (
              <Card className="bg-slate-800/30 border-slate-700/30">
                <CardContent className="py-12 text-center">
                  <Database className="h-12 w-12 text-slate-600 mx-auto mb-3 opacity-50" />
                  <p className="text-slate-500">No memory chunks stored yet</p>
                  <p className="text-slate-600 text-sm mt-1">
                    Upload documents to populate the vector memory
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-2">
                {recentChunks.map((chunk) => {
                  const isExpanded = expandedChunks.has(chunk.index);
                  const displayText = isExpanded 
                    ? chunk.text 
                    : chunk.text.slice(0, 200) + (chunk.text.length > 200 ? "..." : "");
                  
                  return (
                    <div 
                      key={chunk.index}
                      className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-xs font-mono text-slate-500">
                              #{chunk.index}
                            </span>
                          </div>
                          <p className="text-sm text-slate-200 whitespace-pre-wrap">
                            {displayText}
                          </p>
                          {chunk.text.length > 200 && (
                            <button
                              onClick={() => toggleChunkExpand(chunk.index)}
                              className="text-xs text-blue-400 hover:text-blue-300 mt-2 flex items-center gap-1"
                            >
                              {isExpanded ? (
                                <>
                                  <ChevronUp className="h-3 w-3" /> Show less
                                </>
                              ) : (
                                <>
                                  <ChevronDown className="h-3 w-3" /> Show more
                                </>
                              )}
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          <section>
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Search className="h-5 w-5 text-emerald-400" />
              Semantic Search
            </h2>
            <Card className="bg-slate-800/50 border-slate-700/50">
              <CardContent className="pt-6">
                <div className="flex gap-3 mb-6">
                  <Input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                    placeholder="Ask a question to search your memory..."
                    className="flex-1 bg-slate-900/50 border-slate-700"
                  />
                  <select
                    value={searchK}
                    onChange={(e) => setSearchK(Number(e.target.value))}
                    className="bg-slate-900/50 border border-slate-700 rounded px-3 py-2 text-sm"
                  >
                    {[3, 5, 10, 15, 20].map(n => (
                      <option key={n} value={n}>{n} results</option>
                    ))}
                  </select>
                  <Button 
                    onClick={handleSearch}
                    disabled={searching || !query.trim()}
                  >
                    {searching ? "Searching..." : "Search"}
                  </Button>
                </div>

                {searchResults.length > 0 && (
                  <div className="space-y-3">
                    <p className="text-sm text-slate-400 mb-3">
                      Found {searchResults.length} similar chunks for &quot;{query}&quot;
                    </p>
                    {searchResults.map((result) => {
                      const similarity = distanceToSimilarity(result.score);
                      const similarityClass = getSimilarityColor(similarity);
                      const similarityLabel = getSimilarityLabel(similarity);
                      
                      return (
                        <div 
                          key={result.rank}
                          className="bg-slate-900/50 border border-slate-700/50 rounded-lg p-4"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2">
                                <span className="text-xs font-mono text-slate-500">
                                  #{result.rank}
                                </span>
                                <span className={`px-2 py-0.5 rounded text-xs font-medium ${similarityClass}`}>
                                  {similarity}% match ({similarityLabel})
                                </span>
                              </div>
                              <p className="text-sm text-slate-200">
                                {result.text}
                              </p>
                            </div>
                            <span className="text-xs text-slate-500 font-mono whitespace-nowrap">
                              {result.score.toFixed(2)}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {!searching && searchResults.length === 0 && query && (
                  <p className="text-slate-500 text-center py-4">
                    No results yet. Try a different query.
                  </p>
                )}
              </CardContent>
            </Card>
          </section>
        </div>
      </div>
      <AdminSidebar />
    </div>
  );
}
