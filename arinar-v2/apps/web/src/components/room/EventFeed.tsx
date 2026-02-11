'use client';

import { useState, useEffect, useRef } from 'react';
import styles from './EventFeed.module.css';
import * as api from '@/lib/api';
import { SSEClient } from '@/lib/sseClient';
import { getAccessToken } from '@/lib/supabase';

interface Event {
  event_id: string;
  event_type: string;
  created_at: string;
  payload: any;
  content?: any;
}

interface EventFeedProps {
  debateId: string;
  onPresenceUpdate?: (participantId: string, action: 'join' | 'leave') => void;
  onTyping?: (participantId: string) => void;
}

export default function EventFeed({ debateId, onPresenceUpdate, onTyping }: EventFeedProps) {
  const [events, setEvents] = useState<Event[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected');
  const [error, setError] = useState<string | null>(null);
  const sseClientRef = useRef<SSEClient | null>(null);
  const feedRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (!debateId) return;

    let mounted = true;

    const connect = async () => {
      const streamUrl = api.getStreamUrl(debateId);
      setConnectionStatus('connecting');
      setError(null);

      // Get auth token for SSE
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Accept': 'text/event-stream',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const client = new SSEClient(streamUrl, {
        headers,
        onOpen: () => {
          if (mounted) {
            setConnectionStatus('connected');
            setError(null);
          }
        },
        onMessage: (msg) => {
          if (!mounted) return;

          try {
            const event = JSON.parse(msg.data);
            
            // Filter out keepalive events
            if (event.event_type === 'keepalive') {
              return;
            }

            // Handle presence_update events
            if (event.event_type === 'presence_update' && onPresenceUpdate) {
              const payload = event.payload || event.content;
              if (payload?.participant_id && payload?.action) {
                onPresenceUpdate(payload.participant_id, payload.action);
              }
            }

            // Handle typing events
            if (event.event_type === 'typing' && onTyping) {
              const payload = event.payload || event.content;
              if (payload?.participant_id) {
                onTyping(payload.participant_id);
              }
            }

            setEvents((prev) => [...prev, event]);
            
            // Auto-scroll to bottom if user hasn't scrolled up
            if (autoScroll && feedRef.current) {
              setTimeout(() => {
                feedRef.current?.scrollTo({
                  top: feedRef.current.scrollHeight,
                  behavior: 'smooth',
                });
              }, 100);
            }
          } catch (err) {
            console.error('Failed to parse event:', err);
          }
        },
        onError: (err) => {
          if (mounted) {
            setConnectionStatus('disconnected');
            setError('Connection lost. Attempting to reconnect...');
            console.error('SSE error:', err);
          }
        }
      });

      sseClientRef.current = client;
      client.connect();
    };

    connect();

    return () => {
      mounted = false;
      if (sseClientRef.current) {
        sseClientRef.current.disconnect();
        sseClientRef.current = null;
      }
    };
  }, [debateId, autoScroll, onPresenceUpdate, onTyping]);

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

      {error && (
        <div className={styles.error}>
          <span>⚠</span>
          <span>{error}</span>
        </div>
      )}

      <div
        ref={feedRef}
        className={styles.feed}
        onScroll={handleScroll}
      >
        {events.length === 0 ? (
          <div className={styles.emptyFeed}>
            <p>No events yet. Start the debate to see live updates.</p>
          </div>
        ) : (
          events.map((event) => (
            <EventCard key={event.event_id} event={event} />
          ))
        )}
      </div>

      {!autoScroll && events.length > 0 && (
        <button className={styles.jumpToBottom} onClick={scrollToBottom}>
          ↓ Jump to latest
        </button>
      )}
    </div>
  );
}

function EventCard({ event }: { event: Event }) {
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
    return 'System';
  };

  const getMessage = () => {
    if (event.payload?.message) return event.payload.message;
    if (event.payload?.content) return event.payload.content;
    return null;
  };

  return (
    <div className={styles.event} style={{ '--event-color': getEventColor(event.event_type) } as any}>
      <div className={styles.eventHeader}>
        <div className={styles.eventMeta}>
          <span className={styles.actor}>{getActor()}</span>
          <span className={styles.eventType}>{event.event_type}</span>
        </div>
        <span className={styles.timestamp}>
          {new Date(event.created_at).toLocaleTimeString()}
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
        {expanded ? 'Hide' : 'Show'} details
      </button>

      {expanded && (
        <pre className={styles.details}>
          {JSON.stringify(event.payload, null, 2)}
        </pre>
      )}
    </div>
  );
}
