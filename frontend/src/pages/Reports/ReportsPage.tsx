import React, { useState } from 'react';
import {
  FileText,
  Download,
  Printer,
  Eye,
  Calendar,
  Sparkles,
  CheckCircle2,
  Share2,
} from 'lucide-react';
import { TiltCard } from '../../components/3d/TiltCard';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { Modal } from '../../components/common/Modal';
import { MOCK_REPORTS } from '../../mock/mockData';
import { ReportItem } from '../../types';

export const ReportsPage: React.FC = () => {
  const [reports] = useState<ReportItem[]>(MOCK_REPORTS);
  const [selectedReport, setSelectedReport] = useState<ReportItem | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState<boolean>(false);
  const [isExporting, setIsExporting] = useState<boolean>(false);

  const handleOpenPreview = (rep: ReportItem) => {
    setSelectedReport(rep);
    setIsPreviewOpen(true);
  };

  const handleExport = (format: string) => {
    setIsExporting(true);
    setTimeout(() => {
      setIsExporting(false);
      alert(`Exporting ${selectedReport?.title} in ${format} format.`);
    }, 800);
  };

  return (
    <div className="p-6 md:p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white flex items-center gap-2">
            Executive Financial Reports & Audits
            <Badge variant="cyan" size="sm">
              CPA Ready
            </Badge>
          </h1>
          <p className="text-xs text-finwell-muted mt-1">
            Compliant financial statements, tax schedules, and duplicate audit logs.
          </p>
        </div>

        <Button
          variant="primary"
          glow
          onClick={() => alert('Generating new financial statement report... (Demo action)')}
          icon={<Sparkles className="h-4 w-4" />}
        >
          Generate New Report
        </Button>
      </div>

      {/* Reports Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {reports.map((rep) => (
          <TiltCard
            key={rep.id}
            className="p-6 flex flex-col justify-between border border-white/10 hover:border-finwell-primary/40 transition-all"
          >
            <div>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="rounded-xl bg-finwell-primary/20 p-3 text-finwell-cyan">
                    <FileText className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white">{rep.title}</h3>
                    <p className="text-xs text-finwell-dim mt-0.5">
                      Period: {rep.period} • {rep.file_size}
                    </p>
                  </div>
                </div>

                <Badge variant={rep.file_format === 'PDF' ? 'primary' : 'cyan'} size="sm">
                  {rep.file_format}
                </Badge>
              </div>

              <p className="mt-4 text-xs text-finwell-muted leading-relaxed bg-finwell-surface/50 p-3 rounded-xl border border-white/5">
                {rep.summary}
              </p>
            </div>

            <div className="mt-6 pt-4 border-t border-white/5 flex items-center justify-between text-xs">
              <span className="text-finwell-dim text-[11px]">
                Generated {rep.generated_at}
              </span>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleOpenPreview(rep)}
                  icon={<Eye className="h-3.5 w-3.5" />}
                >
                  Preview
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    setSelectedReport(rep);
                    handleExport(rep.file_format);
                  }}
                  icon={<Download className="h-3.5 w-3.5" />}
                >
                  Export
                </Button>
              </div>
            </div>
          </TiltCard>
        ))}
      </div>

      {/* Report Preview Modal */}
      {selectedReport && (
        <Modal
          isOpen={isPreviewOpen}
          onClose={() => setIsPreviewOpen(false)}
          title={selectedReport.title}
          subtitle={`Reporting Scope: ${selectedReport.period}`}
          maxWidth="xl"
        >
          <div className="space-y-6">
            <div className="rounded-xl border border-white/10 bg-finwell-surface p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-white/5 pb-3">
                <div>
                  <span className="text-[10px] text-finwell-dim uppercase font-bold tracking-wider">
                    Executive Summary Preview
                  </span>
                  <p className="text-sm font-bold text-white mt-0.5">{selectedReport.title}</p>
                </div>
                <Badge variant="success" size="sm">
                  Digitally Signed
                </Badge>
              </div>

              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="rounded-lg bg-finwell-card p-3 border border-white/5">
                  <span className="text-finwell-dim text-[10px] uppercase">Net Cash Margin</span>
                  <p className="text-base font-bold text-finwell-success mt-1">62.01%</p>
                </div>
                <div className="rounded-lg bg-finwell-card p-3 border border-white/5">
                  <span className="text-finwell-dim text-[10px] uppercase">Audited Inflow</span>
                  <p className="text-base font-bold text-white mt-1">$64,700.00</p>
                </div>
                <div className="rounded-lg bg-finwell-card p-3 border border-white/5">
                  <span className="text-finwell-dim text-[10px] uppercase">Tax Deductible</span>
                  <p className="text-base font-bold text-finwell-cyan mt-1">$8,210.40</p>
                </div>
              </div>

              <p className="text-xs text-finwell-muted leading-relaxed">
                {selectedReport.summary} All underlying transactional line items are stored with SHA-256 cryptographic hashes for IRS and corporate governance audits.
              </p>
            </div>

            {/* Modal Footer with Export & Print */}
            <div className="flex items-center justify-between border-t border-white/5 pt-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.print()}
                icon={<Printer className="h-4 w-4" />}
              >
                Print Statement
              </Button>

              <div className="flex items-center gap-3">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleExport('CSV')}
                >
                  Download CSV
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  glow
                  isLoading={isExporting}
                  onClick={() => handleExport('PDF')}
                  icon={<Download className="h-4 w-4" />}
                >
                  Download Full PDF
                </Button>
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
