/**
 * Dialog components for Preflight step
 */

'use client';

import styles from './SetupSteps.module.css';
import { useState, useEffect } from 'react';

interface SkipDialogProps {
  isOpen: boolean;
  skipReason: string;
  onReasonChange: (reason: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
}

export function SkipDialog({
  isOpen,
  skipReason,
  onReasonChange,
  onConfirm,
  onCancel,
}: SkipDialogProps) {
  if (!isOpen) return null;

  return (
    <div className={styles.modalOverlay} onClick={onCancel}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <h3>Skip agent preparation</h3>
        <p style={{ marginTop: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
          Provide a reason for skipping this agent's preparation:
        </p>
        <textarea
          value={skipReason}
          onChange={(e) => onReasonChange(e.target.value)}
          placeholder="e.g., Agent model unavailable, network issues, etc."
          className={styles.textarea}
          style={{ marginTop: '1rem', minHeight: '100px' }}
          autoFocus
        />
        <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
          <button onClick={onCancel} className={styles.btnSecondary}>
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={!skipReason.trim()}
            className={styles.btnPrimary}
          >
            Skip agent
          </button>
        </div>
      </div>
    </div>
  );
}

interface PrepPackDialogProps {
  isOpen: boolean;
  content: string | null;
  participantName: string;
  participantRole: string;
  meetingTitle?: string;
  meetingPurpose?: string;
  materialsCount?: number;
  onClose: () => void;
}

export function PrepPackDialog({ 
  isOpen, 
  content, 
  participantName,
  participantRole,
  meetingTitle,
  meetingPurpose,
  materialsCount = 0,
  onClose 
}: PrepPackDialogProps) {
  if (!isOpen || !content) return null;

  // Parse prep pack content to extract structure
  const parseContent = (rawContent: string) => {
    try {
      // Try to parse as JSON first
      const parsed = JSON.parse(rawContent);
      if (parsed.summary || parsed.key_points) {
        return {
          summary: parsed.summary || '',
          keyPoints: parsed.key_points || [],
          context: parsed.context || '',
          materials: parsed.materials_reviewed || []
        };
      }
    } catch {
      // Fall back to plain text parsing
      const lines = rawContent.split('\n');
      return {
        summary: rawContent.substring(0, 300),
        keyPoints: [],
        context: rawContent,
        materials: []
      };
    }
    return { summary: rawContent, keyPoints: [], context: rawContent, materials: [] };
  };

  const parsedContent = parseContent(content);

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div 
        className={styles.modal} 
        onClick={(e) => e.stopPropagation()} 
        style={{ maxWidth: '800px', maxHeight: '85vh', overflow: 'auto' }}
      >
        {/* Header */}
        <div style={{ 
          borderBottom: '2px solid var(--border)', 
          paddingBottom: '1rem', 
          marginBottom: '1.5rem' 
        }}>
          <h2 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>
            Preparation Report
          </h2>
          <p style={{ 
            margin: '0.5rem 0 0 0', 
            fontSize: '0.875rem', 
            color: 'var(--text-muted)' 
          }}>
            Agent: <strong>{participantName}</strong> • Role: <strong>{participantRole}</strong>
          </p>
        </div>

        {/* Meeting Context */}
        {(meetingTitle || meetingPurpose) && (
          <div style={{ 
            marginBottom: '1.5rem',
            padding: '1rem',
            background: 'var(--bg-panel)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
          }}>
            <h3 style={{ 
              margin: '0 0 0.75rem 0', 
              fontSize: '1rem', 
              fontWeight: 600,
              color: 'var(--accent)'
            }}>
              📋 Meeting Context
            </h3>
            {meetingTitle && (
              <div style={{ marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 500, fontSize: '0.875rem' }}>Title: </span>
                <span style={{ fontSize: '0.875rem' }}>{meetingTitle}</span>
              </div>
            )}
            {meetingPurpose && (
              <div>
                <span style={{ fontWeight: 500, fontSize: '0.875rem' }}>Purpose: </span>
                <span style={{ fontSize: '0.875rem' }}>{meetingPurpose}</span>
              </div>
            )}
          </div>
        )}

        {/* Materials Reviewed */}
        {materialsCount > 0 && (
          <div style={{ 
            marginBottom: '1.5rem',
            padding: '1rem',
            background: '#e8f5e9',
            border: '1px solid #4caf50',
            borderRadius: '8px',
          }}>
            <h3 style={{ 
              margin: '0 0 0.5rem 0', 
              fontSize: '1rem', 
              fontWeight: 600,
              color: '#2e7d32'
            }}>
              ✅ Materials Analyzed
            </h3>
            <p style={{ margin: 0, fontSize: '0.875rem', color: '#2e7d32' }}>
              This agent has reviewed and analyzed <strong>{materialsCount} document(s)</strong> to prepare for the meeting.
            </p>
          </div>
        )}

        {/* Preparation Summary */}
        <div style={{ 
          marginBottom: '1.5rem',
          padding: '1rem',
          background: 'var(--bg-panel)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
        }}>
          <h3 style={{ 
            margin: '0 0 0.75rem 0', 
            fontSize: '1rem', 
            fontWeight: 600 
          }}>
            🎯 Preparation Status
          </h3>
          <div style={{ fontSize: '0.875rem', lineHeight: '1.6' }}>
            <p style={{ margin: '0 0 0.5rem 0' }}>
              <strong>Status:</strong> <span style={{ color: 'var(--success)' }}>✓ Ready</span>
            </p>
            <p style={{ margin: '0 0 0.5rem 0' }}>
              <strong>Materials Reviewed:</strong> {materialsCount} chunk(s)
            </p>
            <p style={{ margin: 0 }}>
              <strong>Grants Used:</strong> 0 tokens
            </p>
          </div>
        </div>

        {/* Detailed Context */}
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ 
            margin: '0 0 0.75rem 0', 
            fontSize: '1rem', 
            fontWeight: 600 
          }}>
            📝 Prepared Context
          </h3>
          <pre
            style={{
              padding: '1rem',
              background: 'var(--bg-panel)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              fontSize: '0.875rem',
              fontFamily: 'ui-monospace, monospace',
              whiteSpace: 'pre-wrap',
              wordWrap: 'break-word',
              maxHeight: '300px',
              overflow: 'auto',
              lineHeight: '1.5',
            }}
          >
            {parsedContent.context || content}
          </pre>
        </div>

        {/* Footer Note */}
        <div style={{ 
          padding: '0.75rem 1rem',
          background: '#fff3cd',
          border: '1px solid #ffc107',
          borderRadius: '8px',
          fontSize: '0.8125rem',
          color: '#856404',
          marginBottom: '1.5rem'
        }}>
          <strong>Note:</strong> In production, this prep pack content will be fetched from the backend with full analysis details.
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
          <button onClick={onClose} className={styles.btnPrimary} style={{ minWidth: '120px' }}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
