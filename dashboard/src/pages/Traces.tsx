import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FileUploader } from '../components/common/FileUploader';
import { TraceViewer } from '../components/trace/TraceViewer';
import { convertKurralToTrace } from '../adapters/kurralAdapter';
import type { KurralArtifact } from '../types/kurral';
import type { TraceRecord, TraceSpan } from '../types/trace';
import { ArrowLeft, Sparkles } from 'lucide-react';

export function Traces() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [artifact, setArtifact] = useState<KurralArtifact | null>(null);
  const [traceData, setTraceData] = useState<{
    traceRecord: TraceRecord;
    spans: TraceSpan[];
  } | null>(null);

  const handleFileLoaded = (loadedArtifact: KurralArtifact) => {
    setArtifact(loadedArtifact);
    const converted = convertKurralToTrace(loadedArtifact);
    setTraceData(converted);
  };

  const loadMockArtifact = async (filename: string) => {
    try {
      const response = await fetch(`/mock-artifacts/${filename}`);
      const data = await response.json();
      handleFileLoaded(data);
      // Update URL to reflect the loaded artifact
      setSearchParams({ artifact: filename });
    } catch (error) {
      console.error('Failed to load mock artifact:', error);
    }
  };

  const resetView = () => {
    setArtifact(null);
    setTraceData(null);
    setSearchParams({});
  };

  // Load artifact from URL parameter on mount
  useEffect(() => {
    const artifactParam = searchParams.get('artifact');
    if (artifactParam && !artifact) {
      loadMockArtifact(artifactParam);
    }
  }, [searchParams]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50/30 to-purple-50/20">
      <div className="max-w-7xl mx-auto p-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <img
              src="/kurral-logo.png"
              alt="Kurral Logo"
              className="w-12 h-12 object-contain"
            />
            <div>
              <h1 className="text-4xl font-bold text-gray-900">Kurral Trace Viewer</h1>
              <p className="text-gray-600 mt-1">
                Visualize and analyze AI agent execution traces
              </p>
            </div>
          </div>
        </div>

        {!artifact ? (
          <>
            {/* Mock Data Quick Load */}
            <div className="mb-6 bg-gradient-to-r from-kurral-blue/10 to-kurral-purple-bright/10 border border-kurral-blue/20 rounded-xl p-6 shadow-sm">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-kurral-blue/20 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-5 h-5 text-kurral-blue" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-gray-900 mb-3">
                    Quick Test - Try Sample Artifacts
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => loadMockArtifact('basic-agent-run.kurral')}
                      className="px-4 py-2 text-sm bg-white border-2 border-kurral-blue/30 rounded-lg hover:bg-kurral-blue hover:text-white hover:border-kurral-blue transition-all shadow-sm font-medium"
                    >
                      Basic Agent Run
                    </button>
                    <button
                      onClick={() => loadMockArtifact('mcp-sse-capture.kurral')}
                      className="px-4 py-2 text-sm bg-white border-2 border-cyan-500/30 rounded-lg hover:bg-cyan-500 hover:text-white hover:border-cyan-500 transition-all shadow-sm font-medium"
                    >
                      MCP SSE Stream
                    </button>
                    <button
                      onClick={() => loadMockArtifact('replay-detailed-ars.kurral')}
                      className="px-4 py-2 text-sm bg-white border-2 border-green-500/30 rounded-lg hover:bg-green-500 hover:text-white hover:border-green-500 transition-all shadow-sm font-medium"
                    >
                      Replay with ARS (0.87)
                    </button>
                    <button
                      onClick={() => loadMockArtifact('complex-sse-multi-stream.kurral')}
                      className="px-4 py-2 text-sm bg-white border-2 border-kurral-purple-bright/30 rounded-lg hover:bg-kurral-purple-bright hover:text-white hover:border-kurral-purple-bright transition-all shadow-sm font-medium"
                    >
                      Multi-Stream Pipeline
                    </button>
                    <button
                      onClick={() => loadMockArtifact('sse-error-handling.kurral')}
                      className="px-4 py-2 text-sm bg-white border-2 border-red-500/30 rounded-lg hover:bg-red-500 hover:text-white hover:border-red-500 transition-all shadow-sm font-medium"
                    >
                      SSE Error Case
                    </button>
                    <button
                      onClick={() => loadMockArtifact('fast-sse-stream.kurral')}
                      className="px-4 py-2 text-sm bg-white border-2 border-orange-500/30 rounded-lg hover:bg-orange-500 hover:text-white hover:border-orange-500 transition-all shadow-sm font-medium"
                    >
                      Fast SSE (11.76 evt/s)
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* File Uploader */}
            <div className="max-w-3xl mx-auto">
              <FileUploader onFileLoaded={handleFileLoaded} />
            </div>
          </>
        ) : (
          <div>
            {/* Back Button */}
            <div className="mb-6">
              <button
                onClick={resetView}
                className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-all shadow-sm text-gray-700 font-medium"
              >
                <ArrowLeft className="w-4 h-4" />
                Load Different Artifact
              </button>
            </div>

            {/* Trace Viewer */}
            {traceData && (
              <TraceViewer
                artifact={artifact}
                traceRecord={traceData.traceRecord}
                spans={traceData.spans}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
