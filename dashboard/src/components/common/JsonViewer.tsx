import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface JsonViewerProps {
  data: any;
  title?: string;
  maxHeight?: string;
}

export function JsonViewer({ data, title, maxHeight = '300px' }: JsonViewerProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const jsonString = JSON.stringify(data, null, 2);

  // Simple syntax highlighting
  const highlightJson = (json: string) => {
    return json
      .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?)/g, (match) => {
        let cls = 'text-green-600'; // string
        if (/:$/.test(match)) {
          cls = 'text-blue-700 font-medium'; // key
        }
        return `<span class="${cls}">${match}</span>`;
      })
      .replace(/\b(true|false)\b/g, '<span class="text-purple-600">$1</span>') // boolean
      .replace(/\b(null)\b/g, '<span class="text-gray-500">$1</span>') // null
      .replace(/\b(-?\d+(\.\d+)?)\b/g, '<span class="text-orange-600">$1</span>'); // number
  };

  return (
    <div className="relative">
      {title && (
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
            {title}
          </h4>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded transition-colors"
            title="Copy JSON"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-green-600" />
                <span className="text-green-600">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      )}
      <div
        className="bg-gray-50 rounded-lg border border-gray-200 overflow-auto font-mono text-xs p-4"
        style={{ maxHeight }}
      >
        <pre
          className="whitespace-pre-wrap break-words"
          dangerouslySetInnerHTML={{ __html: highlightJson(jsonString) }}
        />
      </div>
    </div>
  );
}
