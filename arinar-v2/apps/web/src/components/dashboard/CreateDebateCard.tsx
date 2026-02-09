'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import * as api from '@/lib/api';
import styles from './CreateDebateCard.module.css';

interface CreateDebateCardProps {
  workspaceId: string;
  onDebateCreated?: () => void;
}

export default function CreateDebateCard({ workspaceId, onDebateCreated }: CreateDebateCardProps) {
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [problemStatement, setProblemStatement] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!title.trim()) {
      setError('Title is required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const debate = await api.createDebate(workspaceId, title);
      
      // Navigate to room
      router.push(`/room?debate_id=${debate.debate_id}`);
      
      if (onDebateCreated) {
        onDebateCreated();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create debate');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.card}>
      <h2>Your Challenge</h2>
      <p className={styles.description}>Describe what you need help with—be specific for better insights</p>

      {error && (
        <div className={styles.error}>
          <span>⚠</span>
          <span>{error}</span>
        </div>
      )}

      <div className={styles.form}>
        <label>
          Title
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g., Should we expand to international markets?"
            disabled={loading}
          />
        </label>

        <label>
          Problem Statement <span className={styles.optional}>(optional)</span>
          <textarea
            value={problemStatement}
            onChange={(e) => setProblemStatement(e.target.value)}
            placeholder="Provide context, constraints, and what you're trying to decide. The more detail, the better the insights."
            rows={4}
            disabled={loading}
          />
        </label>

        <button
          onClick={handleCreate}
          disabled={loading || !title.trim()}
          className={styles.btnPrimary}
        >
          {loading ? 'Creating...' : 'Create & Assemble Panel'}
        </button>
      </div>
    </div>
  );
}
