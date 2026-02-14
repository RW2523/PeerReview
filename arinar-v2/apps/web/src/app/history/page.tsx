'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import AppNav from '@/components/layout/AppNav';
import * as api from '@/lib/api';
import type { DebateListItem } from '@/lib/api';
import styles from './history.module.css';

export default function HistoryPage() {
  const router = useRouter();
  const [debates, setDebates] = useState<DebateListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDebate, setSelectedDebate] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<any[]>([]);
  const [summary, setSummary] = useState<any | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'transcript' | 'summary'>('list');

  useEffect(() => {
    loadDebates();
  }, []);

  const loadDebates = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Use proper API endpoint
      const response = await api.listDebates('00000000-0000-0000-0000-000000000101', 50);
      setDebates(response.items || []);
    } catch (err) {
      console.error('Failed to load debates:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load debates';
      
      // Provide helpful error message if backend is not running
      if (errorMessage.includes('Failed to fetch') || errorMessage.includes('fetch')) {
        setError('Unable to connect to backend server. Please ensure the API server is running on http://localhost:8000');
      } else {
        setError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const viewDebateTranscript = async (debateId: string) => {
    setSelectedDebate(debateId);
    setViewMode('transcript');
    
    try {
      // Fetch all events for this debate
      const events = await api.getDebateEvents(debateId);
      setTranscript(events);
    } catch (err) {
      console.error('Failed to load transcript:', err);
      setError('Failed to load transcript');
    }
  };

  const viewDebateSummary = async (debateId: string) => {
    setSelectedDebate(debateId);
    setViewMode('summary');
    
    try {
      const data = await api.getDebateSummary(debateId);
      setSummary(data);
    } catch (err) {
      console.error('Failed to load summary:', err);
      setSummary(null);
    }
  };

  const openInRoom = (debateId: string) => {
    router.push(`/room?debate_id=${debateId}`);
  };

  const getStateBadge = (state: string) => {
    const stateStyles: Record<string, string> = {
      pending: styles.statePending,
      running: styles.stateRunning,
      paused: styles.statePaused,
      ended: styles.stateEnded,
    };
    
    return (
      <span className={`${styles.stateBadge} ${stateStyles[state] || ''}`}>
        {state}
      </span>
    );
  };

  return (
    <>
      <AppNav />
      <div className={styles.historyPage}>
        <div className={styles.container}>
          <header className={styles.header}>
            <div>
              <h1>📜 Debate History</h1>
              <p className={styles.subtitle}>View past debates, transcripts, and summaries</p>
            </div>
            {viewMode !== 'list' && (
              <button onClick={() => { setViewMode('list'); setSelectedDebate(null); }} className={styles.btnBack}>
                ← Back to List
              </button>
            )}
          </header>

          {error && (
            <div className={styles.error}>
              <span>⚠️</span>
              <div>
                <div>{error}</div>
                {error.includes('backend server') && (
                  <div style={{ marginTop: '8px', fontSize: '12px' }}>
                    Start the backend: <code style={{ background: 'var(--surface-0)', padding: '2px 6px', borderRadius: '4px' }}>cd apps/api && python -m uvicorn src.main:app --reload</code>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* List View */}
          {viewMode === 'list' && (
            <div className={styles.debatesList}>
              {loading ? (
                <div className={styles.loading}>
                  <div className={styles.spinner}></div>
                  <p>Loading debates...</p>
                </div>
              ) : debates.length === 0 ? (
                <div className={styles.emptyState}>
                  <span className={styles.emptyIcon}>📭</span>
                  <h3>No debates yet</h3>
                  <p>Create your first debate to get started</p>
                  <button onClick={() => router.push('/setup')} className={styles.btnPrimary}>
                    Create Debate
                  </button>
                </div>
              ) : (
                <div className={styles.grid}>
                  {debates.map((debate) => (
                    <div key={debate.debate_id} className={styles.debateCard}>
                      <div className={styles.cardHeader}>
                        <h3 className={styles.debateTitle}>{debate.title || 'Untitled Debate'}</h3>
                        {getStateBadge(debate.state)}
                      </div>
                      
                      <div className={styles.cardMeta}>
                        <span className={styles.metaItem}>
                          📅 {new Date(debate.created_at).toLocaleDateString()}
                        </span>
                        {debate.participant_count && (
                          <span className={styles.metaItem}>
                            👥 {debate.participant_count} participants
                          </span>
                        )}
                        {debate.message_count && (
                          <span className={styles.metaItem}>
                            💬 {debate.message_count} messages
                          </span>
                        )}
                      </div>

                      <div className={styles.cardActions}>
                        <button 
                          onClick={() => viewDebateTranscript(debate.debate_id)}
                          className={styles.btnSecondary}
                        >
                          📄 Transcript
                        </button>
                        {debate.state === 'ended' && (
                          <button 
                            onClick={() => viewDebateSummary(debate.debate_id)}
                            className={styles.btnSecondary}
                          >
                            📊 Summary
                          </button>
                        )}
                        <button 
                          onClick={() => openInRoom(debate.debate_id)}
                          className={styles.btnPrimary}
                        >
                          🏠 Open
                        </button>
                      </div>

                      <div className={styles.cardId}>
                        ID: {debate.debate_id}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Transcript View */}
          {viewMode === 'transcript' && selectedDebate && (
            <div className={styles.transcriptView}>
              <div className={styles.viewHeader}>
                <h2>📄 Full Transcript</h2>
                <div className={styles.viewActions}>
                  <button onClick={() => openInRoom(selectedDebate)} className={styles.btnPrimary}>
                    Open in Room
                  </button>
                </div>
              </div>

              <div className={styles.transcript}>
                {transcript.length === 0 ? (
                  <div className={styles.emptyState}>
                    <p>No messages in this debate yet</p>
                  </div>
                ) : (
                  transcript.map((event, idx) => {
                    const content = event.content || event.payload || {};
                    const agentName = content.agent_name || content.actor || 'System';
                    const text = content.text || content.message || '';
                    
                    return (
                      <div key={event.event_id || idx} className={styles.message}>
                        <div className={styles.messageHeader}>
                          <span className={styles.messageSender}>{agentName}</span>
                          <span className={styles.messageSeq}>#{event.sequence_number}</span>
                        </div>
                        <div className={styles.messageContent}>
                          {text}
                        </div>
                        {event.event_type === 'human_message' && (
                          <div className={styles.humanBadge}>🎙️ Human Intervention</div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {/* Summary View */}
          {viewMode === 'summary' && selectedDebate && (
            <div className={styles.summaryView}>
              <div className={styles.viewHeader}>
                <h2>📊 Debate Summary</h2>
                <div className={styles.viewActions}>
                  <button onClick={() => viewDebateTranscript(selectedDebate)} className={styles.btnSecondary}>
                    View Transcript
                  </button>
                  <button onClick={() => openInRoom(selectedDebate)} className={styles.btnPrimary}>
                    Open in Room
                  </button>
                </div>
              </div>

              {summary ? (
                <div className={styles.summaryContent}>
                  <section className={styles.summarySection}>
                    <h3>📝 Summary</h3>
                    <p className={styles.summaryText}>{summary.summary}</p>
                  </section>

                  <section className={styles.summarySection}>
                    <h3>📋 Minutes of Meeting</h3>
                    <div className={styles.minutesText}>{summary.minutes}</div>
                  </section>

                  {summary.action_items && summary.action_items.length > 0 && (
                    <section className={styles.summarySection}>
                      <h3>✅ Action Items</h3>
                      <div className={styles.actionItems}>
                        {summary.action_items.map((item: any, idx: number) => (
                          <div key={idx} className={styles.actionItem}>
                            <div className={styles.actionHeader}>
                              <span className={styles.actionPriority} data-priority={item.priority}>
                                {item.priority === 'high' ? '🔴' : item.priority === 'medium' ? '🟡' : '🟢'}
                              </span>
                              <span className={styles.actionOwner}>{item.owner}</span>
                            </div>
                            <p className={styles.actionDescription}>{item.description}</p>
                          </div>
                        ))}
                      </div>
                    </section>
                  )}

                  {summary.generated_at && (
                    <div className={styles.summaryMeta}>
                      Generated on {new Date(summary.generated_at).toLocaleString()}
                      {summary.model_used && ` using ${summary.model_used}`}
                    </div>
                  )}
                </div>
              ) : (
                <div className={styles.emptyState}>
                  <span className={styles.emptyIcon}>📊</span>
                  <h3>No Summary Generated</h3>
                  <p>This debate hasn't been summarized yet</p>
                  <button onClick={() => openInRoom(selectedDebate)} className={styles.btnPrimary}>
                    Open in Room to Generate
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
