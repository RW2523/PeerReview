'use client';

import { useState } from 'react';
import styles from './DebateControls.module.css';
import * as api from '@/lib/api';

interface DebateControlsProps {
  debateId: string;
  currentState: string;
  onStateChange: (newState: string) => void;
}

export default function DebateControls({ debateId, currentState, onStateChange }: DebateControlsProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showEndConfirm, setShowEndConfirm] = useState(false);

  const handleStart = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.startDebate(debateId);
      onStateChange(result.state);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start debate');
    } finally {
      setLoading(false);
    }
  };

  const handlePause = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.pauseDebate(debateId);
      onStateChange(result.state);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to pause debate');
    } finally {
      setLoading(false);
    }
  };

  const handleResume = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.resumeDebate(debateId);
      onStateChange(result.state);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resume debate');
    } finally {
      setLoading(false);
    }
  };

  const handleEnd = async () => {
    setShowEndConfirm(false);
    setLoading(true);
    setError(null);
    try {
      const result = await api.endDebate(debateId);
      onStateChange(result.state);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to end debate');
    } finally {
      setLoading(false);
    }
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
