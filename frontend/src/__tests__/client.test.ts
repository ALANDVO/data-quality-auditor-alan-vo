import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from '../api/client';

describe('ApiClient', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('sets and includes Bearer token in request headers', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: 'usr-1', username: 'testuser', roles: ['admin'] }),
    } as Response);

    api.setToken('test-bearer-token');
    const user = await api.getMe();

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/auth/me',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer test-bearer-token',
        }),
      })
    );
    expect(user.username).toBe('testuser');
  });

  it('throws descriptive error on HTTP failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
      json: async () => ({ detail: 'Forbidden: Insufficient privileges' }),
    } as Response);

    await expect(api.deleteDataset('dataset-1')).rejects.toThrow(
      'Forbidden: Insufficient privileges'
    );
  });
});
