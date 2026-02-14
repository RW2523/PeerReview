import { useState } from 'react';
import * as api from '@/lib/api';
import { ModelSelector } from './ModelSelector';
import styles from './SetupSteps.module.css';

interface ParticipantsStepProps {
  participants: api.SetupParticipant[];
  templates: api.AgentTemplate[];
  agents: api.Agent[];
  enableHost: boolean;
  hostModelId?: string;
  onEnableHostChange: (enabled: boolean) => void;
  onHostModelChange: (modelId: string) => void;
  onAddFromTemplate: (template: api.AgentTemplate) => void;
  onAddExisting: (agent: api.Agent) => void;
  onUpdate: (idx: number, updates: Partial<api.SetupParticipant>) => void;
  onRemove: (idx: number) => void;
  onReorder?: (fromIdx: number, toIdx: number) => void;
}

export function ParticipantsStep({
  participants,
  templates,
  agents,
  enableHost,
  hostModelId,
  onEnableHostChange,
  onHostModelChange,
  onAddFromTemplate,
  onAddExisting,
  onUpdate,
  onRemove,
  onReorder,
}: ParticipantsStepProps) {
  const [editingIdx, setEditingIdx] = useState<number | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [showAllTemplates, setShowAllTemplates] = useState(false);
  const [showAllAgents, setShowAllAgents] = useState(false);
  const [agentSearchQuery, setAgentSearchQuery] = useState('');

  const handleMoveUp = (idx: number) => {
    if (idx > 0 && onReorder) {
      onReorder(idx, idx - 1);
    }
  };

  const handleMoveDown = (idx: number) => {
    if (idx < participants.length - 1 && onReorder) {
      onReorder(idx, idx + 1);
    }
  };

  // Get unique categories (excluding Facilitator since we hide Ultimate Host)
  const categories = ['All', ...Array.from(new Set(templates
    .filter(t => t.category !== 'Facilitator')
    .map(t => t.category)))];
  
  // Filter templates by category and exclude Ultimate Host
  const availableTemplates = templates.filter(t => 
    t.template_id !== 'ultimate-host' && 
    t.role_title !== 'Ultimate Host' &&
    t.label !== 'Ultimate Host (Neutral Moderator)'
  );
  
  const filteredTemplates = selectedCategory === 'All' 
    ? availableTemplates 
    : availableTemplates.filter(t => t.category === selectedCategory);
  
  // Limit templates shown initially (show 6, then "Show more" button)
  const displayedTemplates = showAllTemplates ? filteredTemplates : filteredTemplates.slice(0, 6);
  
  // Filter and limit agents (exclude inline/test agents and Ultimate Host)
  const filteredAgents = agents.filter(agent => 
    agent.name.toLowerCase().includes(agentSearchQuery.toLowerCase()) &&
    !agent.name.includes('(Inline)') &&  // Exclude inline template instances
    !agent.name.includes('Ultimate Host') &&
    agent.name !== 'Test PM Agent' &&
    agent.name !== 'Persistent PM'
  );
  const displayedAgents = showAllAgents ? filteredAgents : filteredAgents.slice(0, 6);
  
  // Check if template is already selected
  const isTemplateSelected = (templateId: string) => {
    return participants.some(p => 
      p.name && templates.find(t => 
        t.template_id === templateId && 
        t.label === p.name
      )
    );
  };
  
  // Check if agent is already selected
  const isAgentSelected = (agentId: string) => {
    return participants.some(p => p.agent_id === agentId);
  };

  return (
    <div className={styles.section}>
      <h2>Assemble Your Panel ({participants.length}/8)</h2>
      <p className={styles.hint}>
        Select AI experts with diverse perspectives. Mix roles, seniority, and thinking styles for richer debates.
        <strong> Min 2, Max 8 participants.</strong>
      </p>

      {/* Ultimate Host Configuration */}
      <div className={styles.hostConfig}>
        <div className={styles.hostHeader}>
          <div className={styles.hostToggle}>
            <input
              type="checkbox"
              id="enable-host"
              checked={enableHost}
              onChange={(e) => onEnableHostChange(e.target.checked)}
            />
            <label htmlFor="enable-host">
              <strong>🏛️ Enable Ultimate Host</strong>
              <span className={styles.hostDescription}>
                Neutral moderator that synthesizes all viewpoints and provides a final decision based on majority consensus
              </span>
            </label>
          </div>
        </div>
        
        {enableHost && (
          <div className={styles.hostSettings}>
            <label>Host AI Model</label>
            <select
              value={hostModelId || 'openai/gpt-4o-mini'}
              onChange={(e) => onHostModelChange(e.target.value)}
              className={styles.modelSelect}
            >
              <option value="openai/gpt-4o-mini">GPT-4o Mini (Fast & Cost-effective)</option>
              <option value="openai/gpt-4o">GPT-4o (Balanced)</option>
              <option value="anthropic/claude-3.5-sonnet">Claude 3.5 Sonnet (Premium)</option>
              <option value="google/gemini-pro-1.5">Gemini Pro 1.5 (Advanced)</option>
            </select>
            <p className={styles.helpText}>
              The host will speak last after all rounds are complete to provide a neutral, fact-based conclusion.
            </p>
          </div>
        )}
      </div>

      <div className={styles.twoColumnLayout}>
        {/* LEFT: Selection Panel */}
        <div className={styles.selectionPanel}>
          {/* Agent Templates */}
          <div className={styles.templates}>
            <div className={styles.templateHeader}>
              <h3>Agent Templates</h3>
              <div className={styles.categoryFilter}>
                {categories.map((category) => (
                  <button
                    key={category}
                    onClick={() => setSelectedCategory(category)}
                    className={`${styles.categoryBtn} ${selectedCategory === category ? styles.categoryBtnActive : ''}`}
                  >
                    {category}
                  </button>
                ))}
              </div>
            </div>
            <div className={styles.templateGrid}>
              {displayedTemplates.map((template) => {
                const isSelected = isTemplateSelected(template.template_id);
                return (
                  <button
                    key={template.template_id}
                    onClick={() => onAddFromTemplate(template)}
                    className={`${styles.templateCard} ${isSelected ? styles.templateCardSelected : ''}`}
                    disabled={participants.length >= 8 || isSelected}
                    title={isSelected ? 'Already selected' : 'Click to add'}
                  >
                    {isSelected && <div className={styles.selectedBadge}>✓</div>}
                    <div className={styles.templateLabel}>{template.label}</div>
                    <div className={styles.templateRole}>{template.role_title}</div>
                    {template.character && (
                      <div className={styles.templateCharacter}>{template.character}</div>
                    )}
                  </button>
                );
              })}
            </div>
            {filteredTemplates.length > 6 && (
              <button
                onClick={() => setShowAllTemplates(!showAllTemplates)}
                className={styles.showMoreBtn}
              >
                {showAllTemplates ? '↑ Show Less' : `↓ Show ${filteredTemplates.length - 6} More Templates`}
              </button>
            )}
          </div>

          {/* Existing Agents */}
          {agents.length > 0 && (
            <div className={styles.templates}>
              <div className={styles.templateHeader}>
                <h3>Existing Agents ({agents.length})</h3>
                <input
                  type="text"
                  placeholder="🔍 Search agents..."
                  value={agentSearchQuery}
                  onChange={(e) => setAgentSearchQuery(e.target.value)}
                  className={styles.searchInput}
                />
              </div>
              <div className={styles.templateGrid}>
                {displayedAgents.map((agent) => {
                  const isSelected = isAgentSelected(agent.agent_id);
                  return (
                    <button
                      key={agent.agent_id}
                      onClick={() => onAddExisting(agent)}
                      className={`${styles.templateCard} ${isSelected ? styles.templateCardSelected : ''}`}
                      disabled={participants.length >= 8 || isSelected}
                      title={isSelected ? 'Already selected' : 'Click to add'}
                    >
                      {isSelected && <div className={styles.selectedBadge}>✓</div>}
                      <div className={styles.templateLabel}>{agent.name}</div>
                      <div className={styles.templateRole}>{agent.role_description || 'Custom Agent'}</div>
                    </button>
                  );
                })}
              </div>
              {filteredAgents.length > 6 && (
                <button
                  onClick={() => setShowAllAgents(!showAllAgents)}
                  className={styles.showMoreBtn}
                >
                  {showAllAgents ? '↑ Show Less' : `↓ Show ${filteredAgents.length - 6} More Agents`}
                </button>
              )}
            </div>
          )}
        </div>

        {/* RIGHT: Selected Participants (Sticky) */}
        <div className={styles.selectedPanel}>
          <div className={styles.selectedPanelSticky}>
            <h3>Selected Participants ({participants.length}/8)</h3>
            {participants.length > 1 && (
              <p className={styles.orderHint}>💡 Use ↑/↓ arrows to define turn order</p>
            )}
            
            {participants.length === 0 && (
              <div className={styles.emptyState}>
                <div className={styles.emptyIcon}>👥</div>
                <p>No participants selected yet</p>
                <span className={styles.emptyHint}>Click templates on the left to add</span>
              </div>
            )}

            {participants
              .filter(p => p.name !== 'Ultimate Host' && p.role_name !== 'Ultimate Host')
              .map((participant, idx) => (
              <div key={idx} className={styles.selectedParticipantCard}>
                <div className={styles.cardHeader}>
                  <div className={styles.participantHeaderLeft}>
                    <span className={styles.turnOrderBadge}>#{idx + 1}</span>
                    <span className={styles.participantName}>
                      {participant.agent_id ? `📌 ${participant.name}` : participant.name}
                    </span>
                  </div>
                  <div className={styles.cardActions}>
                    {onReorder && participants.length > 1 && (
                      <div className={styles.orderControls}>
                        <button
                          onClick={() => handleMoveUp(idx)}
                          disabled={idx === 0}
                          className={styles.btnOrder}
                          title="Move up in turn order"
                        >
                          ↑
                        </button>
                        <button
                          onClick={() => handleMoveDown(idx)}
                          disabled={idx === participants.length - 1}
                          className={styles.btnOrder}
                          title="Move down in turn order"
                        >
                          ↓
                        </button>
                      </div>
                    )}
                    {!participant.agent_id && (
                      <button
                        onClick={() => setEditingIdx(editingIdx === idx ? null : idx)}
                        className={styles.btnEditInline}
                        title="Edit participant"
                      >
                        {editingIdx === idx ? '✕' : '✏️'}
                      </button>
                    )}
                    <button 
                      onClick={() => onRemove(idx)} 
                      className={styles.btnRemoveInline}
                      title="Remove participant"
                    >
                      ×
                    </button>
                  </div>
                </div>
                
                {editingIdx === idx && !participant.agent_id && (
                  <div className={styles.editorPanelInline}>
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
                    <ModelSelector
                      value={participant.model_id || ''}
                      onChange={(modelId) => onUpdate(idx, { model_id: modelId })}
                      placeholder="Select AI model..."
                    />
                    
                    <label>Model Config (JSON)</label>
                    <textarea
                      value={JSON.stringify(participant.model_config || {}, null, 2)}
                      onChange={(e) => {
                        try {
                          onUpdate(idx, { model_config: JSON.parse(e.target.value) });
                        } catch {}
                      }}
                      rows={3}
                      placeholder='{"temperature": 0.7}'
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
