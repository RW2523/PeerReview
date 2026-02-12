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
    console.log('[EventFeed] MOUNTING for debate:', debateId, 'at', new Date().toISOString());

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
            
            // DEBUG: Log every received event
            const filterList = ['keepalive', 'heartbeat', 'presence_update', 'typing', 'system_message', 'state_update', 'stream_end'];
            const willBeFiltered = filterList.includes(event.event_type) || filterList.includes(msg.event);
            
            console.log('[EventFeed] SSE message received:', {
              sseEventType: msg.event,
              eventType: event.event_type,
              eventId: event.event_id,
              sequenceNumber: event.sequence_number,
              actor: event.payload?.agent_name || event.payload?.actor || 'NONE',
              hasEventType: !!event.event_type,
              hasAgentName: !!event.payload?.agent_name,
              willBeFiltered: willBeFiltered,
              filterReason: willBeFiltered ? (filterList.includes(event.event_type) ? 'event_type' : 'sse_event') : 'none',
              timestamp: new Date().toISOString()
            });
            
            // Validate event has minimum required fields
            if (!event || typeof event !== 'object') {
              console.warn('Invalid event received:', event);
              return;
            }

            // Filter out internal system events and noise
            const shouldFilterOut = [
              'keepalive',
              'heartbeat',
              'presence_update',
              'typing',
              'system_message',  // Hide all system state changes (started, paused, etc.)
              'state_update',    // SSE control event (state changes)
              'stream_end',      // SSE control event (stream termination)
            ];
            
            // Also check the SSE event type (msg.event) for control events
            if (shouldFilterOut.includes(event.event_type) || shouldFilterOut.includes(msg.event)) {
              // Still handle presence/typing callbacks
              if (event.event_type === 'presence_update' && onPresenceUpdate) {
                const payload = event.payload || event.content;
                if (payload?.participant_id && payload?.action) {
                  onPresenceUpdate(payload.participant_id, payload.action);
                }
              }
              
              if (event.event_type === 'typing' && onTyping) {
                const payload = event.payload || event.content;
                if (payload?.participant_id) {
                  onTyping(payload.participant_id);
                }
              }
              
              return; // Don't add to feed
            }

            // Ensure event has an ID (generate one if missing)
            if (!event.event_id) {
              event.event_id = `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
              console.warn('Event missing event_id, generated temporary ID:', event.event_id);
            }

            // Only add if not already in state (prevent duplicates)
            setEvents((prev) => {
              const exists = prev.some(e => e.event_id === event.event_id);
              if (exists) {
                console.log('[EventFeed] DUPLICATE event ignored:', event.event_id);
                return prev;
              }
              console.log('[EventFeed] Adding event to feed:', event.event_id, event.event_type);
              return [...prev, event];
            });
            
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
      console.log('[EventFeed] UNMOUNTING for debate:', debateId, 'at', new Date().toISOString());
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
          events.map((event, index) => (
            <EventCard 
              key={event.event_id || `event-${index}-${event.created_at || Date.now()}`} 
              event={event} 
            />
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

  const getEventColor = (type: string | undefined) => {
    if (!type) return 'var(--text-2)';
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
    if (event.payload?.text) return event.payload.text;
    return null;
  };

  return (
    <div className={styles.event} style={{ '--event-color': getEventColor(event.event_type) } as any}>
      <div className={styles.eventHeader}>
        <div className={styles.eventMeta}>
          <span className={styles.actor}>{getActor()}</span>
          <span className={styles.eventType}>{event.event_type || 'unknown'}</span>
        </div>
        <span className={styles.timestamp}>
          {event.created_at ? new Date(event.created_at).toLocaleTimeString() : 'N/A'}
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
