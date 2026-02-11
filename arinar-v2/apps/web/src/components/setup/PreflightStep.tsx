/**
 * Preflight Step - Agent preparation before debate starts
 * Shows per-agent progress, retry/skip actions, and prep pack previews
 */

'use client';

import { useState, useEffect } from 'react';
import * as api from '@/lib/api';
import { usePreflight } from '@/hooks/usePreflight';
import { SkipDialog, PrepPackDialog } from './PreflightDialogs';
import styles from './SetupSteps.module.css';

interface PreflightStepProps {
  debateId: string | null;
  participants: api.SetupParticipant[];
  participantIds: string[];
  onCanContinueChange?: (canContinue: boolean) => void;
  meetingTitle?: string;
  meetingPurpose?: string;
}

export function PreflightStep({
  debateId,
  participants,
  participantIds,
  onCanContinueChange,
  meetingTitle,
  meetingPurpose,
}: PreflightStepProps) {
  const {
    status,
    isPolling,
    error,
    startPreflight,
    retryParticipant,
    skipParticipant,
    isStarted,
    isCompleted,
    canContinue,
    hasFailures,
    readyCount,
    totalCount,
  } = usePreflight();

  const [skipDialogOpen, setSkipDialogOpen] = useState(false);
  const [skipParticipantId, setSkipParticipantId] = useState<string | null>(null);
  const [skipReason, setSkipReason] = useState('');
  const [prepPackDialogOpen, setPrepPackDialogOpen] = useState(false);
  const [prepPackContent, setPrepPackContent] = useState<string | null>(null);
  const [prepPackParticipantId, setPrepPackParticipantId] = useState<string | null>(null);

  // Notify parent when readiness changes
  useEffect(() => {
    if (onCanContinueChange) {
      onCanContinueChange(canContinue);
    }
  }, [canContinue, onCanContinueChange]);

  const handleStartPreflight = async () => {
    if (!debateId) {
      alert('Debate not created yet. Please go back and complete previous steps.');
      return;
    }
    
    try {
      await startPreflight(debateId);
      } catch (err: any) {
      console.error('Failed to start preflight:', err);
    }
  };

  const handleRetry = async (participantId: string) => {
    if (!debateId) return;
    
    try {
      await retryParticipant(debateId, participantId);
    } catch (err: any) {
      console.error('Failed to retry:', err);
    }
  };

  const openSkipDialog = (participantId: string) => {
    setSkipParticipantId(participantId);
    setSkipReason('');
    setSkipDialogOpen(true);
  };

  const handleSkipConfirm = async () => {
    if (!debateId || !skipParticipantId || !skipReason.trim()) return;
    
    try {
      await skipParticipant(debateId, skipParticipantId, skipReason);
      setSkipDialogOpen(false);
      setSkipParticipantId(null);
      setSkipReason('');
    } catch (err: any) {
      console.error('Failed to skip:', err);
    }
  };

  const handleViewPrepPack = async (participantRun: api.ParticipantRunStatus) => {
    if (!participantRun.prep_pack_knowledge_id) return;
    
    // For V1, show a simple preview from metadata
    // In production, you'd fetch the actual prep pack content from agent_knowledge_units
    const preview = `Prep Pack for ${getParticipantName(participantRun.participant_id)}

Status: Ready ✅
Materials reviewed: ${participantRun.metadata?.chunks_processed || 0} chunks
Grants used: ${participantRun.metadata?.grants_used || 0}

[Full prep pack content would be fetched from backend in production]`;
    
    setPrepPackContent(preview);
    setPrepPackParticipantId(participantRun.participant_id);
    setPrepPackDialogOpen(true);
  };

  const getParticipantName = (participantId: string): string => {
    const index = participantIds.indexOf(participantId);
    if (index !== -1 && index < participants.length) {
      return participants[index].name || participants[index].role_description || 'Participant';
    }
    return 'Unknown Participant';
  };

  const getParticipantRole = (participantId: string): string => {
    const index = participantIds.indexOf(participantId);
    if (index !== -1 && index < participants.length) {
      return participants[index].role || participants[index].role_description || 'Agent';
    }
    return 'Agent';
  };

  const getInitials = (name: string): string => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const getStatusPill = (status: string) => {
    const statusMap: Record<string, { label: string; className: string }> = {
      queued: { label: 'Queued', className: styles.statusQueued },
      running: { label: 'Preparing...', className: styles.statusRunning },
      success: { label: 'Ready', className: styles.statusSuccess },
      failed: { label: 'Failed', className: styles.statusFailed },
      skipped: { label: 'Skipped', className: styles.statusSkipped },
    };
    
    const config = statusMap[status] || { label: status, className: '' };
    
    return (
      <span className={`${styles.statusPill} ${config.className}`}>
        {config.label}
      </span>
    );
  };

  if (!debateId) {
    return (
      <div className={styles.stepContent}>
        <h2>Prepare your panel</h2>
        <div className={styles.alert} style={{ marginTop: '1.5rem' }}>
          <p>⚠️ Debate not created yet. Please complete previous steps first.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.stepContent}>
      <h2>Prepare your panel</h2>
      <p className={styles.stepDescription}>
        Agents review your materials and allowed past context before the room starts.
      </p>

      {error && (
        <div className={styles.alert} style={{ marginTop: '1.5rem', marginBottom: '1.5rem' }}>
          <p>⚠️ {error}</p>
        </div>
      )}

      {!isStarted && (
        <div style={{ marginTop: '2rem' }}>
          <button
            onClick={handleStartPreflight}
            className={styles.btnPrimary}
            style={{ padding: '1rem 2rem', fontSize: '1rem' }}
          >
            Start preparation
          </button>
          <p style={{ marginTop: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
            This will gather context and prepare each agent. Takes ~5-15 seconds per agent.
          </p>
        </div>
      )}

      {isStarted && (
        <>
          <div className={styles.progressBar} style={{ marginTop: '1.5rem' }}>
            <div className={styles.progressBarLabel}>
              {readyCount} / {totalCount} ready
            </div>
            <div className={styles.progressBarTrack}>
              <div
                className={styles.progressBarFill}
                style={{ width: `${(readyCount / totalCount) * 100}%` }}
              />
            </div>
          </div>

          <div className={styles.participantsList} style={{ marginTop: '2rem' }}>
            {status?.participant_runs.map((participantRun) => {
              const name = getParticipantName(participantRun.participant_id);
              const initials = getInitials(name);

              return (
                <div key={participantRun.participant_run_id} className={styles.participantCard}>
                  <div className={styles.participantAvatar}>
                    {initials}
                  </div>
                  <div className={styles.participantInfo}>
                    <div className={styles.participantName}>{name}</div>
                    {getStatusPill(participantRun.status)}
                  </div>
                  <div className={styles.participantActions}>
                    {participantRun.status === 'failed' && (
                      <button
                        onClick={() => handleRetry(participantRun.participant_id)}
                        className={styles.btnSecondary}
                        style={{ fontSize: '0.875rem', padding: '0.5rem 1rem' }}
                      >
                        Retry
                      </button>
                    )}
                    {(participantRun.status === 'queued' ||
                      participantRun.status === 'running' ||
                      participantRun.status === 'failed') && (
                      <button
                        onClick={() => openSkipDialog(participantRun.participant_id)}
                        className={styles.btnSecondary}
                        style={{ fontSize: '0.875rem', padding: '0.5rem 1rem' }}
                      >
                        Skip
                      </button>
                    )}
                    {participantRun.status === 'success' && participantRun.prep_pack_knowledge_id && (
                      <button
                        onClick={() => handleViewPrepPack(participantRun)}
                        className={styles.btnSecondary}
                        style={{ fontSize: '0.875rem', padding: '0.5rem 1rem' }}
                      >
                        View prep pack
                      </button>
                    )}
                    {participantRun.status === 'skipped' && participantRun.skip_reason && (
                      <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                        {participantRun.skip_reason}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {hasFailures && !isCompleted && (
            <div className={styles.alert} style={{ marginTop: '1.5rem' }}>
              <p>
                ⚠️ Some agents failed to prepare. You can retry individual agents or skip them to continue.
              </p>
            </div>
          )}

          {canContinue && hasFailures && (
            <div className={styles.alert} style={{ marginTop: '1.5rem' }}>
              <p>
                ⚠️ Some agents are skipped or failed. The debate will proceed with reduced context for these agents.
              </p>
            </div>
          )}

          {isPolling && (
            <div style={{ marginTop: '1.5rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              <span>Updating status...</span>
            </div>
          )}
        </>
      )}

      <SkipDialog
        isOpen={skipDialogOpen}
        skipReason={skipReason}
        onReasonChange={setSkipReason}
        onConfirm={handleSkipConfirm}
        onCancel={() => setSkipDialogOpen(false)}
      />

      <PrepPackDialog
        isOpen={prepPackDialogOpen}
        content={prepPackContent}
        participantName={prepPackParticipantId ? getParticipantName(prepPackParticipantId) : 'Unknown'}
        participantRole={prepPackParticipantId ? getParticipantRole(prepPackParticipantId) : 'Unknown'}
        meetingTitle={meetingTitle}
        meetingPurpose={meetingPurpose}
        materialsCount={prepPackParticipantId && status ? 
          status.participant_runs.find(r => r.participant_id === prepPackParticipantId)?.metadata?.chunks_processed || 0 
          : 0
        }
        onClose={() => {
          setPrepPackDialogOpen(false);
          setPrepPackParticipantId(null);
        }}
      />
    </div>
  );
}
