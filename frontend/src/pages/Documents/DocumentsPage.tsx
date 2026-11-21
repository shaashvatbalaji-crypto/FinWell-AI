import React, { useState, useEffect, useRef } from 'react';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Database,
  Search,
  ArrowRight,
  FileCheck,
  Cpu,
} from 'lucide-react';
import { TiltCard } from '../../components/3d/TiltCard';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import {
  documentService,
  STAGE_DESCRIPTIONS,
} from '../../services/documents/documentService';
import { DocumentRecord, DocumentProcessingStage } from '../../types';

export const DocumentsPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadStage, setUploadStage] = useState<DocumentProcessingStage>('uploaded');
  const [uploadPercent, setUploadPercent] = useState<number>(0);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const pipelineStages: { stage: DocumentProcessingStage; label: string; icon: React.ReactNode }[] = [
    { stage: 'uploaded', label: 'Uploaded', icon: <UploadCloud className="h-4 w-4" /> },
    { stage: 'validating', label: 'Validating', icon: <FileCheck className="h-4 w-4" /> },
    { stage: 'extracting_transactions', label: 'Extracting', icon: <Cpu className="h-4 w-4" /> },
    { stage: 'normalizing', label: 'Normalizing', icon: <ArrowRight className="h-4 w-4" /> },
    { stage: 'validating_records', label: 'Validating Records', icon: <CheckCircle2 className="h-4 w-4" /> },
    { stage: 'saving_records', label: 'Saving Records', icon: <Database className="h-4 w-4" /> },
    { stage: 'ready_for_ai', label: 'Ready for AI', icon: <Sparkles className="h-4 w-4" /> },
  ];

  const loadDocuments = async () => {
    const list = await documentService.getDocuments();
    setDocuments(list);
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleFileUpload = async (file: File) => {
    setIsUploading(true);
    setUploadPercent(10);
    setUploadStage('uploaded');

    try {
      await documentService.uploadDocument(file, (stage, percent) => {
        setUploadStage(stage);
        setUploadPercent(percent);
      });
      await loadDocuments();
    } finally {
      setTimeout(() => {
        setIsUploading(false);
        setUploadPercent(0);
      }, 1200);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileUpload(e.target.files[0]);
    }
  };

  return (
    <div className="p-6 md:p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white flex items-center gap-2">
            Statement Ingestion & Vector Pipeline
            <Badge variant="cyan" size="sm">
              7-Step RAG
            </Badge>
          </h1>
          <p className="text-xs text-finwell-muted mt-1">
            Automated PDF extraction into structured MySQL rows and high-dimensional ChromaDB embeddings.
          </p>
        </div>
      </div>

      {/* Drag and Drop Upload Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`relative overflow-hidden rounded-3xl border-2 border-dashed p-8 md:p-12 text-center cursor-pointer transition-all duration-300 ${
          isDragging
            ? 'border-finwell-cyan bg-finwell-cyan/10 shadow-glow-cyan'
            : 'border-white/10 bg-finwell-card/60 hover:border-finwell-primary/50 hover:bg-finwell-surface/50'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={handleFileInputChange}
        />

        <div className="flex flex-col items-center justify-center space-y-3">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-finwell-primary/20 text-finwell-cyan shadow-glow-sm">
            <UploadCloud className="h-8 w-8" />
          </div>

          <h3 className="text-base font-bold text-white">
            Drag and drop your financial PDF statement here
          </h3>
          <p className="text-xs text-finwell-muted max-w-md">
            Supports bank statements, credit card logs, and investment disclosures.
            (Demo simulation — no sensitive banking documents are uploaded to external servers).
          </p>

          <Button variant="secondary" size="sm" className="mt-2 pointer-events-none">
            Or Browse Files on Machine
          </Button>
        </div>
      </div>

      {/* Live 7-Step Visual Processing Timeline (active during upload) */}
      {isUploading && (
        <TiltCard className="p-6 border-finwell-primary/40 shadow-glow-md space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-finwell-cyan opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-finwell-cyan"></span>
              </span>
              <h4 className="text-sm font-bold text-white">
                Neural Ingestion Pipeline Running: {STAGE_DESCRIPTIONS[uploadStage]}
              </h4>
            </div>
            <span className="font-mono text-xs font-bold text-finwell-cyan">{uploadPercent}%</span>
          </div>

          {/* Progress bar */}
          <div className="h-2 w-full rounded-full bg-finwell-surface overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-finwell-primary via-finwell-cyan to-finwell-violet transition-all duration-300"
              style={{ width: `${uploadPercent}%` }}
            />
          </div>

          {/* 7-Step Pills */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 pt-2">
            {pipelineStages.map((st, idx) => {
              const currentIdx = pipelineStages.findIndex((p) => p.stage === uploadStage);
              const isPast = idx < currentIdx;
              const isCurrent = idx === currentIdx;

              return (
                <div
                  key={st.stage}
                  className={`rounded-xl p-2.5 text-center text-xs flex flex-col items-center gap-1 border transition-all ${
                    isCurrent
                      ? 'border-finwell-cyan bg-finwell-cyan/15 text-white shadow-glow-sm'
                      : isPast
                      ? 'border-finwell-primary/40 bg-finwell-primary/10 text-finwell-primary'
                      : 'border-white/5 bg-finwell-surface/40 text-finwell-dim'
                  }`}
                >
                  <span className="text-sm">{st.icon}</span>
                  <span className="text-[10px] font-semibold truncate w-full">{st.label}</span>
                </div>
              );
            })}
          </div>
        </TiltCard>
      )}

      {/* Uploaded Documents List */}
      <TiltCard className="p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-white/5 pb-4">
          <div>
            <h3 className="text-base font-bold text-white">Indexed Financial Documents</h3>
            <p className="text-xs text-finwell-dim mt-0.5">
              Verified statements parsed by FinWell ingestion workers
            </p>
          </div>
          <Badge variant="cyan" size="sm">
            {documents.length} Statements Active
          </Badge>
        </div>

        <div className="divide-y divide-white/5">
          {documents.map((doc) => (
            <div
              key={doc.document_id}
              className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-white/[0.01] transition-colors"
            >
              <div className="flex items-start gap-3.5">
                <div className="rounded-xl bg-finwell-surface p-2.5 text-finwell-primary border border-white/5">
                  <FileText className="h-6 w-6" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">{doc.filename}</h4>
                  <p className="text-xs text-finwell-dim mt-0.5">
                    {doc.institution_detected} • {(doc.file_size_bytes / 1024 / 1024).toFixed(2)} MB • Period: {doc.statement_period}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-6 text-xs">
                <div className="text-right">
                  <span className="text-[10px] text-finwell-dim uppercase font-semibold">Transactions Extracted</span>
                  <p className="font-bold text-white mt-0.5">{doc.extracted_transactions_count} rows</p>
                </div>

                <div className="text-right">
                  <span className="text-[10px] text-finwell-dim uppercase font-semibold">ChromaDB Status</span>
                  <p className="font-semibold text-finwell-success mt-0.5 flex items-center gap-1 justify-end">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Ready for AI
                  </p>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => alert(`Document #${doc.document_id} preview is ready for viewer integration.`)}
                >
                  Inspect
                </Button>
              </div>
            </div>
          ))}
        </div>
      </TiltCard>
    </div>
  );
};
