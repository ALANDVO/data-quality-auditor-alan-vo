import React, { useState, useEffect } from 'react';
import {
  api,
  UserProfile,
  DatasetListItem,
  DatasetDetail,
  AuditRunResponse,
  DriftAnalysisResponse,
  RemediationPlaybookResponse,
} from './api/client';
import { Navbar } from './components/Navbar';
import { DatasetManager } from './components/DatasetManager';
import { AuditScorecardView } from './components/AuditScorecardView';
import { DriftView } from './components/DriftView';
import { RemediationView } from './components/RemediationView';

type Tab = 'datasets' | 'audit' | 'drift' | 'remediation';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('datasets');
  const [user, setUser] = useState<UserProfile | null>(null);
  const [activeRole, setActiveRole] = useState<string>('analyst');
  const [datasets, setDatasets] = useState<DatasetListItem[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<DatasetListItem | null>(null);
  const [datasetDetail, setDatasetDetail] = useState<DatasetDetail | null>(null);
  const [currentAudit, setCurrentAudit] = useState<AuditRunResponse | null>(null);
  const [driftResult, setDriftResult] = useState<DriftAnalysisResponse | null>(null);
  const [playbook, setPlaybook] = useState<RemediationPlaybookResponse | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3500);
  };

  // Switch demo roles
  const handleRoleSwitch = async (role: string) => {
    try {
      setLoading(true);
      const res = await api.getDemoToken(role);
      api.setToken(res.access_token);
      setActiveRole(role);
      const me = await api.getMe();
      setUser(me);
      showToast(`Switched active role to: ${role.toUpperCase()}`);
    } catch (err: any) {
      setError(`Failed to switch role: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    const initAuthAndData = async () => {
      try {
        setLoading(true);
        // Default to analyst in demo mode
        const tokenRes = await api.getDemoToken('analyst');
        api.setToken(tokenRes.access_token);
        const me = await api.getMe();
        setUser(me);

        // Fetch datasets
        await refreshDatasets();
      } catch (err: any) {
        setError(`Initialization error: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };
    initAuthAndData();
  }, []);

  const refreshDatasets = async () => {
    const res = await api.listDatasets();
    setDatasets(res.items);
    if (res.items.length > 0 && !selectedDataset) {
      await handleSelectDataset(res.items[0]);
    }
  };

  const handleSelectDataset = async (d: DatasetListItem) => {
    setSelectedDataset(d);
    try {
      const detail = await api.getDataset(d.id);
      setDatasetDetail(detail);
    } catch (err: any) {
      showToast(`Error loading dataset details: ${err.message}`);
    }
  };

  const handleCreateDataset = async (name: string, type: 'csv' | 'json', content: string) => {
    try {
      const created = await api.createDataset(name, type, content);
      showToast(`Dataset '${created.name}' successfully ingested!`);
      await refreshDatasets();
      await handleSelectDataset(created);
    } catch (err: any) {
      setError(`Failed to ingest dataset: ${err.message}`);
    }
  };

  const handleDeleteDataset = async (id: string) => {
    try {
      await api.deleteDataset(id);
      showToast('Dataset deleted');
      if (selectedDataset?.id === id) {
        setSelectedDataset(null);
        setDatasetDetail(null);
        setCurrentAudit(null);
        setPlaybook(null);
      }
      await refreshDatasets();
    } catch (err: any) {
      setError(`Failed to delete dataset: ${err.message}`);
    }
  };

  const handleRunAudit = async (datasetId: string, includeLlm: boolean) => {
    try {
      setLoading(true);
      const audit = await api.runAudit(datasetId, includeLlm);
      setCurrentAudit(audit);
      showToast(`Quality audit complete! Grade: ${audit.grade}`);

      // Fetch remediation playbook automatically
      const pb = await api.getPlaybook(audit.id);
      setPlaybook(pb);

      setActiveTab('audit');
    } catch (err: any) {
      setError(`Audit execution failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleExportMarkdown = async (auditId: string) => {
    try {
      const md = await api.exportAuditMarkdown(auditId);
      const blob = new Blob([md], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_${auditId.slice(0, 8)}.md`;
      a.click();
      URL.revokeObjectURL(url);
      showToast('Markdown report exported');
    } catch (err: any) {
      setError(`Export failed: ${err.message}`);
    }
  };

  const handleRunDrift = async (targetId: string, baselineId: string, includeLlm: boolean) => {
    try {
      setLoading(true);
      const res = await api.runDrift(targetId, baselineId, includeLlm);
      setDriftResult(res);
      showToast(`Drift analysis complete. Score: ${(res.drift_score * 100).toFixed(1)}%`);
    } catch (err: any) {
      setError(`Drift analysis failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadScript = async () => {
    if (!currentAudit) return;
    try {
      const script = await api.exportScript(currentAudit.id);
      const blob = new Blob([script], { type: 'text/x-python' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `clean_pipeline_${currentAudit.id.slice(0, 8)}.py`;
      a.click();
      URL.revokeObjectURL(url);
      showToast('Remediation script downloaded');
    } catch (err: any) {
      setError(`Download failed: ${err.message}`);
    }
  };

  return (
    <div className="app-container">
      <Navbar
        user={user}
        onRoleSwitch={handleRoleSwitch}
        activeRole={activeRole}
      />

      {toast && <div className="toast-notification">{toast}</div>}

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button className="btn-close" onClick={() => setError(null)}>✕</button>
        </div>
      )}

      <main className="main-content">
        <nav className="tab-navigation">
          <button
            className={`tab-btn ${activeTab === 'datasets' ? 'active' : ''}`}
            onClick={() => setActiveTab('datasets')}
          >
            1. Datasets & Ingestion
          </button>
          <button
            className={`tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
            onClick={() => setActiveTab('audit')}
          >
            2. Quality Scorecard {currentAudit ? `(${currentAudit.grade})` : ''}
          </button>
          <button
            className={`tab-btn ${activeTab === 'drift' ? 'active' : ''}`}
            onClick={() => setActiveTab('drift')}
          >
            3. Schema & Feature Drift
          </button>
          <button
            className={`tab-btn ${activeTab === 'remediation' ? 'active' : ''}`}
            onClick={() => setActiveTab('remediation')}
          >
            4. Remediation Playbook {playbook ? `(${playbook.rules.length})` : ''}
          </button>
        </nav>

        {loading ? (
          <div className="loading-state">
            <div className="spinner" />
            <p>Loading application data...</p>
          </div>
        ) : (
          <div className="tab-panel">
            {activeTab === 'datasets' && (
              <DatasetManager
                datasets={datasets}
                selectedDataset={selectedDataset}
                onSelectDataset={handleSelectDataset}
                onCreateDataset={handleCreateDataset}
                onDeleteDataset={handleDeleteDataset}
                datasetDetail={datasetDetail}
                onRunAudit={handleRunAudit}
                userRole={activeRole}
              />
            )}

            {activeTab === 'audit' && (
              <AuditScorecardView
                auditRun={currentAudit}
                onExportMarkdown={handleExportMarkdown}
              />
            )}

            {activeTab === 'drift' && (
              <DriftView
                datasets={datasets}
                driftResult={driftResult}
                onRunDrift={handleRunDrift}
                userRole={activeRole}
              />
            )}

            {activeTab === 'remediation' && (
              <RemediationView
                playbook={playbook}
                onDownloadScript={handleDownloadScript}
              />
            )}
          </div>
        )}
      </main>

      <footer className="footer">
        <p>
          Built by <strong>Alan Vo</strong> (<a href="mailto:alanvo@gmail.com">alanvo@gmail.com</a>) • GitHub: <a href="https://github.com/ALANDVO" target="_blank" rel="noreferrer">ALANDVO</a>
        </p>
      </footer>
    </div>
  );
};
