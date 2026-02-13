'use client';

import { useState, useEffect, useCallback, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import AppNav from '@/components/layout/AppNav';
import DebateSelector from '@/components/room/DebateSelector';
import EventFeed from '@/components/room/EventFeed';
import DebateControls from '@/components/room/DebateControls';
import AgentBehaviorsPanel from '@/components/room/AgentBehaviorsPanel';
import InterveneComposer from '@/components/room/InterveneComposer';
import SummaryReport from '@/components/room/SummaryReport';
import { useDebateRoom } from '@/hooks/useDebateRoom';
import * as api from '@/lib/api';
import styles from './room.module.css';

/**
 * Room Page - Live Debate Control Center
 * 
 * Data Isolation: All components receive debateId prop and only fetch/display
 * data for that specific debate. No cross-debate data leakage.
 * - EventFeed: filters events by debateId via WebSocket stream
 * - DebateControls: actions scoped to debateId
 * - InterveneComposer: interventions sent to debateId
 * - SummaryReport: summary generated for debateId
 * - AgendaPanel: localStorage keyed by debateId
 */
function RoomPageContent() {
  const searchParams = useSearchParams();
  const [debateId, setDebateId] = useState<string | null>(null);
  const [debateTitle, setDebateTitle] = useState<string>('');
  const [debateState, setDebateState] = useState<string>('pending');
  const [participants, setParticipants] = useState<{ name: string; id: string }[]>([]);
  const [onlineParticipants, setOnlineParticipants] = useState<Set<string>>(new Set());
  const [typingParticipants, setTypingParticipants] = useState<Set<string>>(new Set());
  const typingTimersRef = useRef<Map<string, NodeJS.Timeout>>(new Map());
  const [policyConfig, setPolicyConfig] = useState<any>(null);

  const handleDebateLoaded = (id: string, title: string, state: string) => {
    setDebateId(id);
    setDebateTitle(title);
    setDebateState(state.toLowerCase()); // Normalize to lowercase
    console.log('🎯 Debate loaded:', { id, title, state: state.toLowerCase() });
  };

  // Auto-load debate from URL params (e.g., from setup flow)
  useEffect(() => {
    const debateIdFromUrl = searchParams.get('debate_id');
    if (debateIdFromUrl && !debateId) {
      // Auto-load the debate
      api.getDebate(debateIdFromUrl)
        .then(debate => {
          handleDebateLoaded(debate.debate_id, debate.title || 'Untitled', debate.state);
          setPolicyConfig(debate.policy_config || {});
          console.log('📊 Policy Config loaded:', debate.policy_config);
        })
        .catch(err => {
          console.error('Failed to auto-load debate:', err);
        });
    }
  }, [searchParams, debateId]);

  // WebSocket connection for realtime room transport (single connection owner)
  const { events, sendCommand, connectionStatus } = useDebateRoom({
    debateId: debateId || '',
    enabled: !!debateId && debateState !== 'ended',
  });

  // Update policy config when new agent messages arrive (to update progress indicator)
  useEffect(() => {
    if (!debateId) return;
    
    const hasNewAgentMessage = events.some(e => e.type === 'agent_message');
    if (hasNewAgentMessage) {
      api.getDebate(debateId)
        .then(debate => {
          setPolicyConfig(debate.policy_config || {});
        })
        .catch(err => {
          console.error('Failed to refresh debate policy:', err);
        });
    }
  }, [events.length, debateId]); // Only when events array length changes

  // Presence join/leave via WebSocket
  useEffect(() => {
    if (!debateId || !sendCommand || connectionStatus !== 'connected') return;

    // Join presence via WebSocket
    sendCommand('join_presence').catch(err => {
      console.error('Failed to join presence:', err);
    });

    // Leave presence on unmount
    return () => {
      sendCommand('leave_presence').catch(err => {
        console.error('Failed to leave presence:', err);
      });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debateId, connectionStatus]); // sendCommand is stable (useCallback with empty deps), exclude from deps to prevent infinite loop

  // Handle presence updates from EventFeed
  const handlePresenceUpdate = useCallback((participantId: string, action: 'join' | 'leave') => {
    setOnlineParticipants(prev => {
      const next = new Set(prev);
      if (action === 'join') {
        next.add(participantId);
      } else {
        next.delete(participantId);
      }
      return next;
    });
  }, []);

  // Handle typing signals from EventFeed
  const handleTyping = useCallback((participantId: string) => {
    // Add to typing set
    setTypingParticipants(prev => new Set(prev).add(participantId));

    // Clear existing timer
    const existing = typingTimersRef.current.get(participantId);
    if (existing) {
      clearTimeout(existing);
    }

    // Remove after 3 seconds
    const timer = setTimeout(() => {
      setTypingParticipants(prev => {
        const next = new Set(prev);
        next.delete(participantId);
        return next;
      });
      typingTimersRef.current.delete(participantId);
    }, 3000);

    typingTimersRef.current.set(participantId, timer);
  }, []); // typingTimersRef is stable, exclude from deps

  // Load agenda data from localStorage
  const getAgendaData = () => {
    if (!debateId) return { items: [], outcome: { desired: '', criteria: [] } };
    
    const agendaKey = `agenda_${debateId}`;
    const outcomeKey = `outcome_${debateId}`;
    
    const items = JSON.parse(localStorage.getItem(agendaKey) || '[]');
    const outcome = JSON.parse(localStorage.getItem(outcomeKey) || '{"desired":"","criteria":[]}');
    
    return { items, outcome };
  };

  // Fetch participants when debate is loaded
  useEffect(() => {
    if (!debateId) return;

    api.getDebate(debateId)
      .then((data) => {
        if (data.participants) {
          const participantList = data.participants
            .filter((p: any) => {
              const name = p.agent_config?.name || p.role_name || '';
              return name !== 'Ultimate Host';
            })
            .map((p: any) => ({
              id: p.participant_id,
              name: p.agent_config?.name || p.role_name || 'Unknown Agent',
            }));
          setParticipants(participantList);
          console.log('👥 Participants loaded:', participantList.length);
        }
      })
      .catch((err) => console.error('Failed to fetch participants:', err));
  }, [debateId]);

  return (
    <>
      <AppNav />
      <div className={styles.room}>
      {/* Left Rail: Meeting Info */}
      <aside className={styles.leftRail}>
        <div className={styles.meetingInfo}>
          {debateId && (
            <>
              <div className={styles.debateHeader}>
                <h1 className={styles.debateTitle}>{debateTitle || 'Untitled'}</h1>
                <div className={`${styles.stateBadge} ${styles[`state-${debateState}`]}`}>
                  {debateState?.toUpperCase()}
                </div>
              </div>
              
              {(() => {
                const shouldShow = policyConfig && debateState?.toLowerCase() === 'running' && participants.length > 0;
                console.log('🎯 Progress Indicator Check:', {
                  policyConfig: !!policyConfig,
                  debateState: debateState?.toLowerCase(),
                  participantsCount: participants.length,
                  shouldShow,
                  maxRounds: policyConfig?.max_rounds,
                  timeboxMinutes: policyConfig?.timebox_minutes
                });
                return shouldShow;
              })() && (
                <div className={styles.progressIndicator}>
                  {policyConfig.max_rounds && (
                    <>
                      <div className={styles.progressLabel}>🎯 Round Progress</div>
                      <div className={styles.progressValue}>
                        Round {Math.floor(((policyConfig.total_turns_taken || 0) / participants.length)) + 1} / {policyConfig.max_rounds}
                      </div>
                      <div className={styles.progressBar}>
                        <div 
                          className={styles.progressFill} 
                          style={{
                            width: `${Math.min(100, ((Math.floor(((policyConfig.total_turns_taken || 0) / participants.length)) + 1) / policyConfig.max_rounds) * 100)}%`
                          }}
                        />
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-2)', marginTop: '8px' }}>
                        {policyConfig.total_turns_taken || 0} / {policyConfig.max_rounds * participants.length} total turns
                      </div>
                    </>
                  )}
                  {policyConfig.timebox_minutes && !policyConfig.max_rounds && (
                    <>
                      <div className={styles.progressLabel}>⏱️ Time Limit</div>
                      <div className={styles.progressValue}>
                        {policyConfig.timebox_minutes} minutes
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-2)', marginTop: '4px' }}>
                        Debate will auto-end after time limit
                      </div>
                    </>
                  )}
                </div>
              )}
              
              <section className={styles.section}>
                <h3>Participants</h3>
                <div className={styles.participantsList}>
                  {participants.length === 0 ? (
                    <p className={styles.empty}>No participants yet</p>
                  ) : (
                    participants.map((p) => (
                      <div key={p.id} className={styles.participant}>
                        {p.name}
                      </div>
                    ))
                  )}
                </div>
              </section>
            </>
          )}
        </div>
      </aside>

      {/* Center: Conversation Feed */}
      <main className={styles.center}>
        {!debateId ? (
          <div className={styles.emptyState}>
            <h2>Welcome to the Decision Room</h2>
            <p>Load an existing debate or create a new one to get started.</p>
            <div className={styles.selectorWrapper}>
              <DebateSelector onDebateLoaded={handleDebateLoaded} />
            </div>
          </div>
        ) : debateState === 'ended' ? (
          <SummaryReport
            debateId={debateId}
            agendaData={getAgendaData()}
          />
        ) : (
          <>
            <EventFeed 
              events={events}
              connectionStatus={connectionStatus}
              onPresenceUpdate={handlePresenceUpdate}
              onTyping={handleTyping}
            />
            <InterveneComposer 
              debateId={debateId} 
              participants={participants}
              sendCommand={sendCommand}
            />
          </>
        )}
      </main>

      {/* Right Panel: Controls & Agenda */}
      <aside className={styles.rightPanel}>
        {debateId ? (
          <>
            <DebateControls
              debateId={debateId}
              currentState={debateState}
              policyConfig={policyConfig}
              totalTurns={policyConfig?.total_turns_taken || 0}
              participantCount={participants.length}
              onPolicyUpdate={() => {
                // Refetch policy config when extended
                api.getDebate(debateId).then(debate => {
                  setPolicyConfig(debate.policy_config || {});
                }).catch(err => console.error('Failed to refresh policy:', err));
              }}
              onStateChange={(newState) => setDebateState(newState)}
              sendCommand={sendCommand}
            />
            
            <AgentBehaviorsPanel debateId={debateId} events={events} />
          </>
        ) : (
          <div className={styles.hint}>
            Load or create a debate to access controls.
          </div>
        )}
      </aside>
      </div>
    </>
  );
}

export default function RoomPage() {
  return (
    <Suspense fallback={<div>Loading room...</div>}>
      <RoomPageContent />
    </Suspense>
  );
}
