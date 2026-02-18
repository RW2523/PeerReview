/**
 * DocumentPanel - Document view in debate room
 */
'use client';

import React from 'react';
import { useDocumentSync } from '@/lib/hooks/useDocumentSync';
import { useDocument } from '@/lib/hooks/useDocument';
import DocumentEditor from '@/components/document/DocumentEditor';
import DiagramSection from '@/components/document/DiagramSection';
import { SectionType } from '@/lib/document/types';
import styles from './DocumentPanel.module.css';

interface DocumentPanelProps {
  debateId: string;
  documentId: string | null;
  userId: string;
  userName: string;
}

export default function DocumentPanel({
  debateId,
  documentId,
  userId,
  userName,
}: DocumentPanelProps) {
  const { document, loading } = useDocument(documentId || undefined);
  const { provider, connected, synced } = useDocumentSync(
    documentId,
    userId,
    userName
  );

  if (!documentId) {
    return (
      <div className={styles.panel}>
        <div className={styles.empty}>
          <span className={styles.emptyIcon}>📄</span>
          <h3>No Document</h3>
          <p>Enable documentation in setup to create a shared document</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className={styles.panel}>
        <div className={styles.loading}>Loading document...</div>
      </div>
    );
  }

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h2>{document?.title || 'Document'}</h2>
        <div className={styles.status}>
          <span className={connected ? styles.connected : styles.disconnected}>
            {connected ? '🟢' : '🔴'} {connected ? 'Connected' : 'Disconnected'}
          </span>
          {synced && <span className={styles.synced}>✓ Synced</span>}
        </div>
      </div>

      <div className={styles.sections}>
        {document?.sections.map((section) => (
          <div key={section.section_id || section.id} className={styles.section}>
            <div className={styles.sectionHeader}>
              <h3>{section.section_title || section.title || 'Untitled Section'}</h3>
              <div className={styles.sectionMeta}>
                {section.assigned_agent_name && (
                  <span className={styles.assignedAgent}>
                    👤 {section.assigned_agent_name}
                  </span>
                )}
                {section.word_limit && (
                  <span className={styles.wordLimit}>
                    {section.word_count || 0}/{section.word_limit} words
                  </span>
                )}
              </div>
            </div>
            
            {section.section_type === 'diagram' ? (
              <DiagramSection
                mermaidCode={section.content || 'graph TD\n  A[Start]-->B[End]'}
                editable={false}
              />
            ) : (
              <DocumentEditor
                provider={provider}
                sectionKey={section.section_key || section.key}
                userName={userName}
                placeholder={`Write ${(section.section_title || section.title || 'section').toLowerCase()}...`}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
