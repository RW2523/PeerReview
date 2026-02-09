'use client';

import { useState, useEffect } from 'react';
import AppNav from '@/components/layout/AppNav';
import DebateSelector from '@/components/room/DebateSelector';
import EventFeed from '@/components/room/EventFeed';
import DebateControls from '@/components/room/DebateControls';
import AgendaPanel from '@/components/room/AgendaPanel';
import InterveneComposer from '@/components/room/InterveneComposer';
import SummaryReport from '@/components/room/SummaryReport';
import * as api from '@/lib/api';
import styles from './room.module.css';

/**
 * Room Page - Live Debate Control Center
 * 
 * Data Isolation: All components receive debateId prop and only fetch/display
 * data for that specific debate. No cross-debate data leakage.
 * - EventFeed: filters events by debateId via SSE stream
 * - DebateControls: actions scoped to debateId
 * - InterveneComposer: interventions sent to debateId
 * - SummaryReport: summary generated for debateId
 * - AgendaPanel: localStorage keyed by debateId
 */
export default function RoomPage() {
  const [debateId, setDebateId] = useState<string | null>(null);
  const [debateTitle, setDebateTitle] = useState<string>('');
  const [debateState, setDebateState] = useState<string>('pending');
  const [participants, setParticipants] = useState<{ name: string; id: string }[]>([]);

  const handleDebateLoaded = (id: string, title: string, state: string) => {
    setDebateId(id);
    setDebateTitle(title);
    setDebateState(state);
  };

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
          const participantList = data.participants.map((p: any) => ({
            id: p.participant_id,
            name: p.agent_config?.name || p.agent_id || 'Unknown',
          }));
          setParticipants(participantList);
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
          <div className={styles.branding}>
            <h2>Arinar</h2>
            <span className={styles.subtitle}>Decision Room</span>
          </div>
          
          {debateId && (
            <>
              <div className={styles.debateHeader}>
                <h1 className={styles.debateTitle}>{debateTitle || 'Untitled'}</h1>
                <div className={`${styles.stateBadge} ${styles[`state-${debateState}`]}`}>
                  {debateState}
                </div>
              </div>
              
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
            <EventFeed debateId={debateId} />
            <InterveneComposer debateId={debateId} participants={participants} />
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
              onStateChange={(newState) => setDebateState(newState)}
            />
            
            <AgendaPanel debateId={debateId} />
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
