'use client';

import { useState } from 'react';
import { useEventStream, DebateEvent } from '@/hooks/useEventStream';
import * as api from '@/lib/api';
import styles from './operator.module.css';

export default function OperatorPage() {
  const [debateId, setDebateId] = useState('');
  const [activeDebateId, setActiveDebateId] = useState<string | null>(null);
  const [interventionText, setInterventionText] = useState('');
  const [status, setStatus] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);

  const streamUrl = activeDebateId ? api.getStreamUrl(activeDebateId) : null;
  const stream = useEventStream(streamUrl);

  const handleCreate = async () => {
    setIsLoading(true);
    setStatus('Creating debate...');
    try {
      const result = await api.createDebate(
        '00000000-0000-0000-0000-000000000101', // Test workspace
        'M2 Test Debate'
      );
      setDebateId(result.debate_id);
      setActiveDebateId(result.debate_id);
      setStatus(`Created: ${result.debate_id}`);
    } catch (err: any) {
      setStatus(`Error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStart = async () => {
    if (!debateId) return;
    setIsLoading(true);
    setStatus('Starting...');
    try {
      const result = await api.startDebate(debateId);
      setStatus(`Started - State: ${result.state}`);
      if (!activeDebateId) setActiveDebateId(debateId);
    } catch (err: any) {
      setStatus(`Error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePause = async () => {
    if (!debateId) return;
    setIsLoading(true);
    setStatus('Pausing...');
    try {
      const result = await api.pauseDebate(debateId);
      setStatus(`Paused - State: ${result.state}`);
    } catch (err: any) {
      setStatus(`Error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResume = async () => {
    if (!debateId) return;
    setIsLoading(true);
    setStatus('Resuming...');
    try {
      const result = await api.resumeDebate(debateId);
      setStatus(`Resumed - State: ${result.state}`);
    } catch (err: any) {
      setStatus(`Error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEnd = async () => {
    if (!debateId) return;
    setIsLoading(true);
    setStatus('Ending...');
    try {
      const result = await api.endDebate(debateId);
      setStatus(`Ended - State: ${result.state}`);
    } catch (err: any) {
      setStatus(`Error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleIntervene = async () => {
    if (!debateId || !interventionText.trim()) return;
    setIsLoading(true);
    setStatus('Intervening...');
    try {
      await api.intervene(debateId, { message: interventionText });
      setStatus('Intervention sent');
      setInterventionText('');
    } catch (err: any) {
      setStatus(`Error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConnect = () => {
    if (debateId && !activeDebateId) {
      setActiveDebateId(debateId);
      setStatus('Connecting to stream...');
    }
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>Arinar M2 Operator</h1>
        <p className={styles.subtitle}>Realtime Debate Controls</p>
      </header>

      <div className={styles.content}>
        {/* Control Panel */}
        <div className={styles.panel}>
          <h2>Debate Controls</h2>
          
          <div className={styles.section}>
            <label>Debate ID</label>
            <div className={styles.inputGroup}>
              <input
                type="text"
                value={debateId}
                onChange={(e) => setDebateId(e.target.value)}
                placeholder="Enter debate ID or create new"
                disabled={isLoading}
              />
              {!activeDebateId && debateId && (
                <button onClick={handleConnect} disabled={isLoading}>
                  Connect
                </button>
              )}
            </div>
          </div>

          <div className={styles.buttonGrid}>
            <button onClick={handleCreate} disabled={isLoading} className={styles.btnPrimary}>
              Create New
            </button>
            <button onClick={handleStart} disabled={isLoading || !debateId}>
              Start
            </button>
            <button onClick={handlePause} disabled={isLoading || !debateId}>
              Pause
            </button>
            <button onClick={handleResume} disabled={isLoading || !debateId}>
              Resume
            </button>
            <button onClick={handleEnd} disabled={isLoading || !debateId} className={styles.btnDanger}>
              End
            </button>
          </div>

          <div className={styles.section}>
            <label>Intervention</label>
            <textarea
              value={interventionText}
              onChange={(e) => setInterventionText(e.target.value)}
              placeholder="Type intervention message (use @agent to tag)"
              rows={3}
              disabled={isLoading || !debateId}
            />
            <button
              onClick={handleIntervene}
              disabled={isLoading || !debateId || !interventionText.trim()}
            >
              Send Intervention
            </button>
          </div>

          {status && (
            <div className={styles.status}>
              <strong>Status:</strong> {status}
            </div>
          )}
        </div>

        {/* Live Feed */}
        <div className={styles.panel}>
          <h2>Live Feed</h2>
          
          <div className={styles.streamStatus}>
            <span className={stream.isConnected ? styles.connected : styles.disconnected}>
              {stream.isConnected ? '● Connected' : '○ Disconnected'}
            </span>
            {stream.debateState && (
              <span className={styles.state}>
                State: {stream.debateState.toUpperCase()}
              </span>
            )}
          </div>

          {stream.error && (
            <div className={styles.error}>{stream.error}</div>
          )}

          <div className={styles.events}>
            {stream.events.length === 0 && (
              <p className={styles.empty}>No events yet. Start or connect to a debate.</p>
            )}
            {stream.events.map((event) => (
              <div key={event.event_id} className={styles.event}>
                <div className={styles.eventHeader}>
                  <span className={styles.eventType}>{event.event_type}</span>
                  <span className={styles.eventSeq}>#{event.sequence_number}</span>
                </div>
                <div className={styles.eventPayload}>
                  {JSON.stringify(event.payload, null, 2)}
                </div>
                <div className={styles.eventTime}>
                  {new Date(event.occurred_at).toLocaleTimeString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
