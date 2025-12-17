import React, { useCallback, useState } from 'react';
import { Upload, FileJson, AlertCircle } from 'lucide-react';
import type { KurralArtifact } from '../../types/kurral';

interface FileUploaderProps {
  onFileLoaded: (artifact: KurralArtifact) => void;
}

export function FileUploader({ onFileLoaded }: FileUploaderProps) {
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);
      setLoading(true);

      if (!file.name.endsWith('.kurral') && !file.name.endsWith('.json')) {
        setError('Please upload a .kurral or .json file');
        setLoading(false);
        return;
      }

      try {
        const text = await file.text();
        const artifact = JSON.parse(text) as KurralArtifact;

        // Basic validation
        if (!artifact.kurral_id || (!artifact.tool_calls && !artifact.mcp_tool_calls)) {
          setError('Invalid Kurral artifact format - missing required fields');
          setLoading(false);
          return;
        }

        onFileLoaded(artifact);
        setLoading(false);
      } catch (err) {
        setError('Failed to parse file: ' + (err as Error).message);
        setLoading(false);
      }
    },
    [onFileLoaded]
  );

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);

      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFile(e.dataTransfer.files[0]);
      }
    },
    [handleFile]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      e.preventDefault();

      if (e.target.files && e.target.files[0]) {
        handleFile(e.target.files[0]);
      }
    },
    [handleFile]
  );

  return (
    <div className="w-full">
      <div
        className={`
          relative border-2 border-dashed rounded-xl p-12
          transition-all duration-200
          ${
            dragActive
              ? 'border-kurral-blue bg-blue-50 scale-105'
              : 'border-gray-300 hover:border-kurral-blue hover:bg-gray-50'
          }
          ${loading ? 'opacity-50 pointer-events-none' : ''}
        `}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          id="file-upload"
          type="file"
          accept=".kurral,.json"
          onChange={handleChange}
          className="hidden"
          disabled={loading}
        />

        <label
          htmlFor="file-upload"
          className="flex flex-col items-center justify-center cursor-pointer"
        >
          <div className={`flex items-center justify-center w-20 h-20 mb-4 rounded-full ${
            dragActive ? 'bg-kurral-blue/20' : 'bg-kurral-blue/10'
          } transition-colors`}>
            {loading ? (
              <div className="w-10 h-10 border-4 border-kurral-blue border-t-transparent rounded-full animate-spin" />
            ) : dragActive ? (
              <Upload className="w-10 h-10 text-kurral-blue animate-bounce" />
            ) : (
              <FileJson className="w-10 h-10 text-kurral-blue" />
            )}
          </div>

          <p className="text-xl font-semibold text-gray-900 mb-2">
            {loading ? 'Loading...' : dragActive ? 'Drop your file here' : 'Upload Kurral Artifact'}
          </p>

          <p className="text-sm text-gray-600 mb-4">
            {loading ? 'Parsing artifact...' : 'Drag & drop or click to browse'}
          </p>

          <p className="text-xs text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
            .kurral or .json files only
          </p>
        </label>
      </div>

      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-900">Upload Error</p>
            <p className="text-sm text-red-700 mt-1">{error}</p>
          </div>
        </div>
      )}
    </div>
  );
}
