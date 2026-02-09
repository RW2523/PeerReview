'use client';

import { useState } from 'react';
import styles from './DebateSelector.module.css';

interface DebateSelectorProps {
  onDebateLoaded: (debateId: string, title: string, state: string) => void;
}

export default function DebateSelector({ onDebateLoaded }: DebateSelectorProps) {
  const [mode, setMode] = useState<'load' | 'create'>('load');
  const [debateIdInput, setDebateIdInput] = useState('');
  const [titleInput, setTitleInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLoad = async () => {
    if (!debateIdInput.trim()) {
      setError('Please enter a debate ID');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/debates/${debateIdInput}`);
      
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Debate not found');
        }
        throw new Error(`Failed to load debate: ${response.statusText}`);
      }

      const debate = await response.json();
      onDebateLoaded(debate.debate_id, debate.title || 'Untitled', debate.state);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load debate');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!titleInput.trim()) {
      setError('Please enter a debate title');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      // Use default workspace from demo (can be made configurable later)
      const payload = {
        workspace_id: '00000000-0000-0000-0000-000000000001',
        title: titleInput,
        policy_config: {
          problem_statement: 'Created from Decision Room',
        },
      };

      const response = await fetch(`${API_URL}/debates`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Failed to create debate: ${response.statusText}`);
      }

      const debate = await response.json();
      onDebateLoaded(debate.debate_id, debate.title, debate.state);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create debate');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.selector}>
      <div className={styles.header}>
        <h2>Load or Create Debate</h2>
      </div>

      <div className={styles.modeToggle}>
        <button
          className={mode === 'load' ? styles.active : ''}
          onClick={() => setMode('load')}
        >
          Load Existing
        </button>
        <button
          className={mode === 'create' ? styles.active : ''}
          onClick={() => setMode('create')}
        >
          Create New
        </button>
      </div>

      {error && (
        <div className={styles.error}>
          <span>⚠</span>
          <span>{error}</span>
        </div>
      )}

      {mode === 'load' ? (
        <div className={styles.form}>
          <label>
            Debate ID
            <input
              type="text"
              value={debateIdInput}
              onChange={(e) => setDebateIdInput(e.target.value)}
              placeholder="Enter debate ID (UUID)"
              disabled={loading}
            />
          </label>
          <button
            onClick={handleLoad}
            disabled={loading}
            className={styles.btnPrimary}
          >
            {loading ? 'Loading...' : 'Load Debate'}
          </button>
        </div>
      ) : (
        <div className={styles.form}>
          <label>
            Debate Title
            <input
              type="text"
              value={titleInput}
              onChange={(e) => setTitleInput(e.target.value)}
              placeholder="Enter debate title"
              disabled={loading}
            />
          </label>
          <button
            onClick={handleCreate}
            disabled={loading}
            className={styles.btnPrimary}
          >
            {loading ? 'Creating...' : 'Create Debate'}
          </button>
        </div>
      )}
    </div>
  );
}
