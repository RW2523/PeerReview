/**
 * React hook for WebSocket-based debate room transport
 * 
 * Manages WebSocket lifecycle, event subscription, and command dispatch
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { WSClient, WSEventEnvelope, WSCommandType, ConnectionStatus, WSAckMessage } from '@/lib/wsClient';
import { getAccessToken } from '@/lib/supabase';

export interface UseDebateRoomOptions {
  debateId: string;
  enabled?: boolean;
  sinceSequence?: number;
}

export interface UseDebateRoomResult {
  events: WSEventEnvelope[];
  connectionStatus: ConnectionStatus;
  sendCommand: (command: WSCommandType, payload?: Record<string, any>) => Promise<WSAckMessage>;
  clearEvents: () => void;
}

export function useDebateRoom(options: UseDebateRoomOptions): UseDebateRoomResult {
  const { debateId, enabled = true, sinceSequence = 0 } = options;
  
  const [events, setEvents] = useState<WSEventEnvelope[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const clientRef = useRef<WSClient | null>(null);

  // Event handler
  const handleEvent = useCallback((event: WSEventEnvelope) => {
    setEvents((prev) => {
      // Deduplicate by event_id (belt and suspenders with client-side dedupe)
      if (event.event_id && prev.some(e => e.event_id === event.event_id)) {
        return prev;
      }
      return [...prev, event];
    });
  }, []);

  // Connection status handler
  const handleConnectionChange = useCallback((status: ConnectionStatus) => {
    setConnectionStatus(status);
  }, []);

  // Auth token provider
  const getAuthToken = useCallback(async () => {
    const token = await getAccessToken();
    if (!token) {
      throw new Error('No auth token available');
    }
    return token;
  }, []);

  // Error handler
  const handleError = useCallback((error: Error) => {
    console.error('[useDebateRoom] WebSocket error:', error);
  }, []);

  // Initialize WebSocket client
  useEffect(() => {
    if (!enabled || !debateId) {
      return;
    }

    const client = new WSClient({
      debateId,
      getAuthToken,
      onEvent: handleEvent,
      onConnectionChange: handleConnectionChange,
      onError: handleError,
      sinceSequence,
      baseUrl: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
    });

    clientRef.current = client;
    client.connect();

    return () => {
      client.disconnect();
      clientRef.current = null;
    };
  }, [debateId, enabled, sinceSequence, getAuthToken, handleEvent, handleConnectionChange, handleError]);

  // Command dispatcher
  const sendCommand = useCallback(async (command: WSCommandType, payload?: Record<string, any>): Promise<WSAckMessage> => {
    if (!clientRef.current) {
      throw new Error('WebSocket client not initialized');
    }
    
    if (clientRef.current.getStatus() !== 'connected') {
      throw new Error('WebSocket not connected');
    }

    return clientRef.current.sendCommand(command, payload);
  }, []);

  // Clear events (for testing or reset)
  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  return {
    events,
    connectionStatus,
    sendCommand,
    clearEvents,
  };
}
