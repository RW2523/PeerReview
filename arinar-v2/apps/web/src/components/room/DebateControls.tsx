'use client';

import { useState } from 'react';
import styles from './DebateControls.module.css';

interface DebateControlsProps {
  debateId: string;
  currentState: string;
  onStateChange: (newState: string) => void;
}

export default function DebateControls({ debateId, currentState, onStateChange }: DebateControlsProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showEndConfirm, setShowEndConfirm] = useState(false);

  const callEndpoint = async (action: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`http://localhost:8000/debates/${debateId}/${action}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to ${action} debate`);
      }

      const result = await response.json();
      onStateChange(result.state || action + 'ed');
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStart = () => callEndpoint('start');
  const handlePause = () => callEndpoint('pause');
  const handleResume = () => callEndpoint('resume');
  
  const handleEnd = () => {
    setShowEndConfirm(false);
    callEndpoint('end');
  };

  const canStart = currentState === 'pending';
  const canPause = currentState === 'running';
  const canResume = currentState === 'paused';
  const canEnd = currentState === 'running' || currentState === 'paused';

  return (
    <div className={styles.controls}>
      <h3>Controls</h3>

      {error && (
        <div className={styles.error}>
          <span>⚠</span>
          <span>{error}</span>
        </div>
      )}

      <div className={styles.buttons}>
        <button
          onClick={handleStart}
          disabled={!canStart || loading}
          className={canStart ? styles.btnPrimary : ''}
        >
          {loading && currentState === 'pending' ? 'Starting...' : 'Start'}
        </button>

        <button
          onClick={handlePause}
          disabled={!canPause || loading}
        >
          {loading && currentState === 'running' ? 'Pausing...' : 'Pause'}
        </button>

        <button
          onClick={handleResume}
          disabled={!canResume || loading}
          className={canResume ? styles.btnPrimary : ''}
        >
          {loading && currentState === 'paused' ? 'Resuming...' : 'Resume'}
        </button>

        <button
          onClick={() => setShowEndConfirm(true)}
          disabled={!canEnd || loading}
          className={styles.btnDanger}
        >
          End Meeting
        </button>
      </div>

      {showEndConfirm && (
        <div className={styles.confirmSheet}>
          <div className={styles.confirmContent}>
            <h4>End this meeting?</h4>
            <p>
              Once ended, the debate will stop and you can generate a summary with minutes and action items.
            </p>
            <div className={styles.confirmActions}>
              <button
                className={styles.btnSecondary}
                onClick={() => setShowEndConfirm(false)}
              >
                Cancel
              </button>
              <button
                className={styles.btnDanger}
                onClick={handleEnd}
              >
                End Meeting
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
