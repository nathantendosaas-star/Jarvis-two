import React, { useMemo, useState } from "react";
import {
  Folder,
  FileCode,
  FileImage,
  FileText,
  Search,
  ChevronDown,
  FileVideo,
  FileAudio,
  ArrowLeft
} from "lucide-react";
import { FileNode } from "../types";

interface FilesViewProps {
  files: FileNode[];
  setFiles: React.Dispatch<React.SetStateAction<FileNode[]>>;
  triggerNotification: (title: string, msg: string, type: any) => void;
}

export default function FilesView({
  files,
}: FilesViewProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedFile, setSelectedFile] = useState<FileNode | null>(null);

  const handleSelectFile = (file: FileNode) => {
    setSelectedFile(file);
  };

  const formatBytes = (bytes = 0) => {
    if (bytes === 0) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    return `${(bytes / Math.pow(1024, index)).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
  };

  const workspaceStats = useMemo(() => {
    const walk = (nodes: FileNode[]): { fileCount: number; directoryCount: number; bytes: number } => {
      return nodes.reduce(
        (stats, node) => {
          if (node.isDirectory) {
            const childStats = walk(node.children || []);
            return {
              fileCount: stats.fileCount + childStats.fileCount,
              directoryCount: stats.directoryCount + 1 + childStats.directoryCount,
              bytes: stats.bytes + childStats.bytes,
            };
          }

          return {
            fileCount: stats.fileCount + 1,
            directoryCount: stats.directoryCount,
            bytes: stats.bytes + (node.size || 0),
          };
        },
        { fileCount: 0, directoryCount: 0, bytes: 0 },
      );
    };

    return walk(files);
  }, [files]);

  const filteredFiles = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();
    if (!query) return files;

    const filterNode = (node: FileNode): FileNode | null => {
      const matches = node.name.toLowerCase().includes(query) || node.path.toLowerCase().includes(query);
      const children = node.children?.map(filterNode).filter(Boolean) as FileNode[] | undefined;
      if (matches || (children && children.length > 0)) {
        return { ...node, children };
      }
      return null;
    };

    return files.map(filterNode).filter(Boolean) as FileNode[];
  }, [files, searchTerm]);

  const modifiedLabel = selectedFile?.modifiedAt
    ? new Intl.DateTimeFormat(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(selectedFile.modifiedAt))
    : "Unknown";

  const getIcon = (node: FileNode) => {
    if (node.isDirectory) return <Folder className="w-4 h-4 text-blue-400 shrink-0" />;
    switch (node.type) {
      case "code": return <FileCode className="w-4 h-4 text-amber-400 shrink-0" />;
      case "image": return <FileImage className="w-4 h-4 text-emerald-400 shrink-0" />;
      case "markdown": return <FileText className="w-4 h-4 text-purple-400 shrink-0" />;
      case "video": return <FileVideo className="w-4 h-4 text-rose-400 shrink-0" />;
      case "audio": return <FileAudio className="w-4 h-4 text-cyan-400 shrink-0" />;
      default: return <FileText className="w-4 h-4 text-slate-400 shrink-0" />;
    }
  };

  // Render file explorer list recursively
  const renderExplorerNode = (node: FileNode, depth = 0) => {
    const isDir = node.isDirectory;
    const isSelected = selectedFile?.path === node.path;

    return (
      <div key={node.path} className="space-y-0.5">
        <div
          onClick={() => !isDir && handleSelectFile(node)}
          className={`flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs transition-all cursor-pointer select-none ${
            isSelected
              ? "bg-slate-900 text-white font-medium border border-slate-800"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/40 border border-transparent"
          }`}
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
        >
          {isDir ? <ChevronDown className="w-3.5 h-3.5 text-slate-500 shrink-0" /> : <div className="w-3.5 h-3.5 shrink-0" />}
          {getIcon(node)}
          <span className="truncate">{node.name}</span>
          {!isDir && <span className="ml-auto text-[9px] text-slate-600 font-mono">{formatBytes(node.size)}</span>}
        </div>

        {isDir && node.children && (
          <div className="space-y-0.5">
            {node.children.map(child => renderExplorerNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex-1 flex overflow-hidden text-slate-200 h-full relative">
      
      {/* Sidebar: File list and search */}
      <div className={`${selectedFile ? 'hidden md:flex' : 'flex'} w-full md:w-80 border-r border-slate-800/40 p-5 flex-col h-full bg-slate-950/10 shrink-0 z-10 md:static absolute inset-0 bg-jarvis-bg`}>
        
        {/* Search */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search files..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full glass-input pl-9 pr-3 py-2 text-xs h-9"
          />
        </div>

        {/* Tree Explorer */}
        <div className="flex-1 overflow-y-auto space-y-1 pr-1">
          <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wider font-semibold mb-2 px-2 space-y-1">
            <span className="block">Workspace Files</span>
            <span className="block normal-case tracking-normal font-normal text-slate-600">
              {workspaceStats.fileCount} files · {workspaceStats.directoryCount} folders · {formatBytes(workspaceStats.bytes)}
            </span>
          </div>
          {filteredFiles.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl">
              No files match the current search.
            </div>
          ) : (
            filteredFiles.map(node => renderExplorerNode(node))
          )}
        </div>

      </div>

      {/* Editor & Viewer Frame */}
      <div className={`${!selectedFile ? 'hidden md:flex' : 'flex'} flex-1 flex-col overflow-hidden bg-slate-950/20 h-full`}>
        {selectedFile ? (
          <div className="flex-1 flex flex-col overflow-hidden animate-fade-in">
            {/* Toolbar */}
            <div className="px-6 py-3 border-b border-slate-800/40 flex items-center justify-between bg-slate-950/40 shrink-0">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setSelectedFile(null)}
                  className="md:hidden flex items-center justify-center p-1.5 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                </button>
                <div>
                  <span className="text-[10px] font-mono text-slate-500 block">FILE_PATH: {selectedFile.path}</span>
                  <span className="text-xs font-bold text-white mt-0.5 inline-block">{selectedFile.name}</span>
                </div>
              </div>

              <div className="text-[10px] font-mono text-slate-500 text-right">
                <span className="block">{formatBytes(selectedFile.size)}</span>
                <span className="block">{modifiedLabel}</span>
              </div>
            </div>

            {/* Viewer body */}
            <div className="flex-1 overflow-auto p-6">
              {selectedFile.type === "image" ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-8">
                  <div className="relative max-w-sm rounded-xl overflow-hidden border border-slate-800/80 bg-slate-900 shadow-2xl p-4">
                    <div className="aspect-square w-64 bg-gradient-to-tr from-blue-900/40 to-purple-900/40 rounded-lg flex items-center justify-center mb-4 border border-slate-800/40">
                      <FileImage className="w-12 h-12 text-blue-400" />
                    </div>
                    <h3 className="text-xs font-bold text-slate-200 mb-1">{selectedFile.name}</h3>
                    <span className="text-[10px] font-mono text-slate-500">{selectedFile.content}</span>
                  </div>
                </div>
              ) : selectedFile.type === "markdown" ? (
                <div className="max-w-2xl mx-auto prose prose-invert prose-xs text-slate-300 space-y-4">
                  {/* Simplistic render simulation */}
                  <div className="p-5 bg-slate-900/30 border border-slate-800/60 rounded-xl whitespace-pre-wrap leading-relaxed font-sans text-xs">
                    {selectedFile.content}
                  </div>
                </div>
              ) : (
                <pre className="p-5 bg-slate-900/30 border border-slate-800/60 rounded-xl text-xs font-mono text-blue-200 overflow-auto max-w-4xl mx-auto whitespace-pre">
                  <code>{selectedFile.content}</code>
                </pre>
              )}
            </div>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center p-12 text-slate-500">
            <FileCode className="w-12 h-12 text-slate-700 mb-3" />
            <h3 className="text-sm font-bold text-white">No file selected</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm">Click a real file from the workspace tree to inspect its metadata and available contents.</p>
          </div>
        )}
      </div>

    </div>
  );
}
