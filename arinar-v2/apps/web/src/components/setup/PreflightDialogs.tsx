/**
 * Dialog components for Preflight step
 */

'use client';

import styles from './SetupSteps.module.css';

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
  onClose: () => void;
}

export function PrepPackDialog({ isOpen, content, onClose }: PrepPackDialogProps) {
  if (!isOpen || !content) return null;

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()} style={{ maxWidth: '600px' }}>
        <h3>Prep Pack Preview</h3>
        <pre
          style={{
            marginTop: '1rem',
            padding: '1rem',
            background: 'var(--bg-panel)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            fontSize: '0.875rem',
            whiteSpace: 'pre-wrap',
            maxHeight: '400px',
            overflow: 'auto',
          }}
        >
          {content}
        </pre>
        <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
          <button onClick={onClose} className={styles.btnPrimary}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
