import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { App } from '../App';
import { api } from '../api/client';

describe('App Component', () => {
  beforeEach(() => {
    vi.spyOn(api, 'getDemoToken').mockResolvedValue({ access_token: 'fake-token', role: 'analyst' });
    vi.spyOn(api, 'getMe').mockResolvedValue({ id: 'usr-1', username: 'demo-analyst', roles: ['analyst'] });
    vi.spyOn(api, 'listDatasets').mockResolvedValue({ items: [], total: 0 });
  });

  it('renders application brand title and navigation tabs', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Data Quality Auditor')).toBeInTheDocument();
    });

    expect(screen.getByText('Alan Vo | AI & Machine Learning')).toBeInTheDocument();
    expect(screen.getByText('1. Datasets & Ingestion')).toBeInTheDocument();
    expect(screen.getByText(/2. Quality Scorecard/i)).toBeInTheDocument();
    expect(screen.getByText('3. Schema & Feature Drift')).toBeInTheDocument();
    expect(screen.getByText(/4. Remediation Playbook/i)).toBeInTheDocument();
  });
});
