'use client';

import { useState, useRef, useEffect, ReactNode } from 'react';
import styles from './EventFeed.module.css';
import { WSEventEnvelope, ConnectionStatus } from '@/lib/wsClient';

interface EventFeedProps {
  events: WSEventEnvelope[];
  connectionStatus: ConnectionStatus;
  onPresenceUpdate?: (participantId: string, action: 'join' | 'leave') => void;
  onTyping?: (participantId: string) => void;
}

// Simple markdown parser for common patterns
function parseMarkdown(text: string): ReactNode {
  // Split by lines for list handling
  const lines = text.split('\n');
  const result: ReactNode[] = [];
  let key = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    
    // Check for numbered list (1. 2. 3.)
    const numberedMatch = line.match(/^(\d+)\.\s+(.+)$/);
    if (numberedMatch) {
      result.push(
        <div key={key++} className={styles.listItem}>
          <span className={styles.listNumber}>{numberedMatch[1]}.</span>
          <span>{parseInlineMarkdown(numberedMatch[2])}</span>
        </div>
      );
      continue;
    }

    // Regular line with inline markdown
    if (line.trim()) {
      result.push(<div key={key++}>{parseInlineMarkdown(line)}</div>);
    } else {
      result.push(<br key={key++} />);
    }
  }

  return <>{result}</>;
}

// Parse inline markdown (bold, italic, code, mentions)
function parseInlineMarkdown(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;

  // Pattern: **bold**, *italic*, `code`, @mentions
  const pattern = /(\*\*(.+?)\*\*)|(\*(.+?)\*)|(`(.+?)`)|(@[\w-]+)/g;
  
  let match;
  while ((match = pattern.exec(text)) !== null) {
    // Add text before match
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    if (match[1]) {
      // **bold**
      parts.push(<strong key={key++}>{match[2]}</strong>);
    } else if (match[3]) {
      // *italic*
      parts.push(<em key={key++}>{match[4]}</em>);
    } else if (match[5]) {
      // `code`
      parts.push(<code key={key++} className={styles.inlineCode}>{match[6]}</code>);
    } else if (match[7]) {
      // @mention
      parts.push(<span key={key++} className={styles.mention}>{match[7]}</span>);
    }

    lastIndex = pattern.lastIndex;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length > 0 ? parts : [text];
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
          displayEvents.map((event, index) => {
            // Turn = complete round where ALL participants spoke
            const turn = event.payload?.turn;
            const previousEvent = index > 0 ? displayEvents[index - 1] : null;
            const previousTurn = previousEvent?.payload?.turn;
            
            // Show separator when turn number changes
            const showTurnSeparator = turn && turn !== previousTurn;

            return (
              <EventCard 
                key={event.event_id} 
                event={event} 
                showTurnSeparator={showTurnSeparator}
                turnNumber={turn}
              />
            );
          })
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

function EventCard({ event, showTurnSeparator, turnNumber }: { event: WSEventEnvelope; showTurnSeparator?: boolean; turnNumber?: number }) {
  const [expanded, setExpanded] = useState(false);

  const getEventColor = (type: string) => {
    if (type.includes('agent_message')) return '#0070F3';
    if (type.includes('human_message')) return '#0070F3';
    if (type.includes('intervention')) return '#0070F3';
    if (type.includes('summary')) return '#0070F3';
    if (type.includes('error')) return '#E00';
    return '#0070F3';
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

  const getEventTypeLabel = (type: string) => {
    if (type === 'agent_message') return '💬 Message';
    if (type === 'human_message') return '👤 You';
    if (type === 'intervention') return '⚡ Intervention';
    if (type === 'system_message') return '⚙️ System';
    if (type === 'turn_start') return '▶️ Turn Start';
    if (type === 'turn_end') return '⏸️ Turn End';
    if (type === 'state_update') return '📊 State';
    if (type === 'error') return '❌ Error';
    return type.replace(/_/g, ' ');
  };

  return (
    <>
      {showTurnSeparator && turnNumber ? (
        <div className={styles.turnSeparator}>
          <div className={styles.turnLine} />
          <span className={styles.turnLabel}>Turn #{turnNumber}</span>
          <div className={styles.turnLine} />
        </div>
      ) : null}
      <div className={styles.event} style={{ '--event-color': getEventColor(event.type) } as any}>
        <div className={styles.eventHeader}>
          <div className={styles.eventMeta}>
            <span className={styles.actor}>{getActor()}</span>
            <span className={styles.eventType}>{getEventTypeLabel(event.type)}</span>
          </div>
          <span className={styles.timestamp}>
            {event.occurred_at ? new Date(event.occurred_at).toLocaleTimeString() : 'N/A'}
          </span>
        </div>

        {getMessage() && (
          <div className={styles.message}>
            {parseMarkdown(getMessage()!)}
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
    </>
  );
}
