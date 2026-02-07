import { useState } from 'react';
import * as api from '@/lib/api';
import styles from './SetupSteps.module.css';

interface ParticipantsStepProps {
  participants: api.SetupParticipant[];
  templates: api.AgentTemplate[];
  agents: api.Agent[];
  onAddFromTemplate: (template: api.AgentTemplate) => void;
  onAddExisting: (agent: api.Agent) => void;
  onUpdate: (idx: number, updates: Partial<api.SetupParticipant>) => void;
  onRemove: (idx: number) => void;
}

export function ParticipantsStep({
  participants,
  templates,
  agents,
  onAddFromTemplate,
  onAddExisting,
  onUpdate,
  onRemove,
}: ParticipantsStepProps) {
  const [editingIdx, setEditingIdx] = useState<number | null>(null);

  return (
    <div className={styles.section}>
      <h2>Participants ({participants.length}/8)</h2>
      <p className={styles.hint}>Choose agents to participate in the discussion</p>

      <div className={styles.templates}>
        <h3>From Template</h3>
        <div className={styles.templateGrid}>
          {templates.map((template) => (
            <button
              key={template.template_id}
              onClick={() => onAddFromTemplate(template)}
              className={styles.templateCard}
              disabled={participants.length >= 8}
            >
              <div className={styles.templateLabel}>{template.label}</div>
              <div className={styles.templateRole}>{template.role_title}</div>
            </button>
          ))}
        </div>
      </div>

      {agents.length > 0 && (
        <div className={styles.templates}>
          <h3>Existing Agents</h3>
          <div className={styles.templateGrid}>
            {agents.map((agent) => (
              <button
                key={agent.agent_id}
                onClick={() => onAddExisting(agent)}
                className={styles.templateCard}
                disabled={participants.length >= 8}
              >
                <div className={styles.templateLabel}>{agent.name}</div>
                <div className={styles.templateRole}>{agent.role_description || 'Custom Agent'}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className={styles.list}>
        <h3>Selected Participants</h3>
        {participants.map((participant, idx) => (
          <div key={idx} className={styles.participantCard}>
            <div className={styles.cardHeader}>
              <span className={styles.participantName}>
                {participant.agent_id ? '(Reference)' : participant.name}
              </span>
              <div>
                {!participant.agent_id && (
                  <button
                    onClick={() => setEditingIdx(editingIdx === idx ? null : idx)}
                    className={styles.btnEdit}
                  >
                    {editingIdx === idx ? 'Close' : 'Edit'}
                  </button>
                )}
                <button onClick={() => onRemove(idx)} className={styles.btnRemove}>×</button>
              </div>
            </div>
            
            {editingIdx === idx && !participant.agent_id && (
              <div className={styles.editorPanel}>
                <label>Name</label>
                <input
                  type="text"
                  value={participant.name || ''}
                  onChange={(e) => onUpdate(idx, { name: e.target.value })}
                  placeholder="Agent Name"
                />
                
                <label>System Prompt</label>
                <textarea
                  value={participant.system_prompt || ''}
                  onChange={(e) => onUpdate(idx, { system_prompt: e.target.value })}
                  placeholder="You are..."
                  rows={4}
                />
                
                <label>Model ID</label>
                <input
                  type="text"
                  value={participant.model_id || ''}
                  onChange={(e) => onUpdate(idx, { model_id: e.target.value })}
                  placeholder="anthropic/claude-3.5-sonnet"
                />
                
                <label>Model Config (JSON, optional)</label>
                <textarea
                  value={JSON.stringify(participant.model_config || {}, null, 2)}
                  onChange={(e) => {
                    try {
                      onUpdate(idx, { model_config: JSON.parse(e.target.value) });
                    } catch {}
                  }}
                  rows={3}
                  placeholder='{"temperature": 0.7, "max_tokens": 2000}'
                />
              </div>
            )}
          </div>
        ))}
        
        {participants.length === 0 && (
          <p className={styles.empty}>No participants added yet (min 1 required)</p>
        )}
      </div>
    </div>
  );
}
