'use client';

import { useState, useRef, useEffect } from 'react';
import styles from './EventFeed.module.css';
import { WSEventEnvelope, ConnectionStatus } from '@/lib/wsClient';

interface EventFeedProps {
  events: WSEventEnvelope[];
  connectionStatus: ConnectionStatus;
  onPresenceUpdate?: (participantId: string, action: 'join' | 'leave') => void;
  onTyping?: (participantId: string) => void;
}

export default function EventFeed({ events: wsEvents, connectionStatus, onPresenceUpdate, onTyping }: EventFeedProps) {
  const [displayEvents, setDisplayEvents] = useState<WSEventEnvelope[]>([]);
  const feedRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Filter and process WebSocket events
  useEffect(() => {
    const filtered = wsEvents.filter((event) => {
      const shouldFilterOut = [
        'state_update',
        'typing',
        'presence_update',
      ];

      // Handle side-effect events but don't display them
      if (event.type === 'presence_update' && onPresenceUpdate) {
        const action = event.payload?.action;
        const participantId = event.payload?.participant_id;
        if (action && participantId) {
          onPresenceUpdate(participantId, action);
        }
      }

      if (event.type === 'typing' && onTyping) {
        const participantId = event.payload?.participant_id;
        if (participantId && !event.payload?.ping) {
          onTyping(participantId);
        }
      }

      return !shouldFilterOut.includes(event.type);
    });

    setDisplayEvents(filtered);
  }, [wsEvents, onPresenceUpdate, onTyping]);

  // Auto-scroll on new events
  useEffect(() => {
    if (autoScroll && feedRef.current) {
      setTimeout(() => {
        feedRef.current?.scrollTo({
          top: feedRef.current.scrollHeight,
          behavior: 'smooth',
        });
      }, 100);
    }
  }, [displayEvents, autoScroll]);

  const handleScroll = () => {
    if (!feedRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = feedRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    setAutoScroll(isNearBottom);
  };

  const scrollToBottom = () => {
    feedRef.current?.scrollTo({
      top: feedRef.current.scrollHeight,
      behavior: 'smooth',
    });
    setAutoScroll(true);
  };

  return (
    <div className={styles.feedContainer}>
      <div className={styles.feedHeader}>
        <h2>Live Feed</h2>
        <div className={styles.connectionStatus}>
          <span className={`${styles.statusDot} ${styles[connectionStatus]}`} />
          <span className={styles.statusText}>
            {connectionStatus === 'connected' ? 'Connected' : 
             connectionStatus === 'connecting' ? 'Connecting...' : 'Disconnected'}
          </span>
        </div>
      </div>

      <div 
        ref={feedRef}
        className={styles.feed}
        onScroll={handleScroll}
      >
        {displayEvents.length === 0 ? (
          <div className={styles.emptyState}>
            <p>No messages yet. The debate will appear here when it starts.</p>
          </div>
        ) : (
          displayEvents.map((event) => (
            <EventCard key={event.event_id} event={event} />
          ))
        )}
      </div>

      {!autoScroll && displayEvents.length > 0 && (
        <button className={styles.jumpToBottom} onClick={scrollToBottom}>
          ↓ Jump to latest
        </button>
      )}
    </div>
  );
}

function EventCard({ event }: { event: WSEventEnvelope }) {
  const [expanded, setExpanded] = useState(false);

  const getEventColor = (type: string) => {
    if (type.includes('agent_message')) return 'var(--accent)';
    if (type.includes('intervention')) return 'var(--warning)';
    if (type.includes('summary')) return 'var(--success)';
    if (type.includes('error')) return 'var(--danger)';
    return 'var(--text-2)';
  };

  const getActor = () => {
    if (event.payload?.agent_name) return event.payload.agent_name;
    if (event.payload?.actor) return event.payload.actor;
    if (event.sender_type === 'agent') return 'Agent';
    if (event.sender_type === 'user') return 'User';
    return 'System';
  };

  const getMessage = () => {
    if (event.payload?.message) return event.payload.message;
    if (event.payload?.content) return event.payload.content;
    if (event.payload?.text) return event.payload.text;
    return null;
  };

  return (
    <div className={styles.event} style={{ '--event-color': getEventColor(event.type) } as any}>
      <div className={styles.eventHeader}>
        <div className={styles.eventMeta}>
          <span className={styles.actor}>{getActor()}</span>
          <span className={styles.eventType}>{event.type}</span>
        </div>
        <span className={styles.timestamp}>
          {event.occurred_at ? new Date(event.occurred_at).toLocaleTimeString() : 'N/A'}
        </span>
      </div>

      {getMessage() && (
        <div className={styles.message}>
          {getMessage()}
        </div>
      )}

      <button
        className={styles.expandBtn}
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? 'Hide details' : 'Show details'}
      </button>

      {expanded && (
        <div className={styles.details}>
          <div className={styles.detailRow}>
            <span className={styles.detailLabel}>Event ID:</span>
            <span className={styles.detailValue}>{event.event_id}</span>
          </div>
          <div className={styles.detailRow}>
            <span className={styles.detailLabel}>Sequence:</span>
            <span className={styles.detailValue}>#{event.sequence_number}</span>
          </div>
          <div className={styles.detailRow}>
            <span className={styles.detailLabel}>Sender:</span>
            <span className={styles.detailValue}>{event.sender_type} ({event.sender_id || 'system'})</span>
          </div>
          <div className={styles.detailRow}>
            <span className={styles.detailLabel}>Payload:</span>
            <pre className={styles.payloadPre}>{JSON.stringify(event.payload, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
