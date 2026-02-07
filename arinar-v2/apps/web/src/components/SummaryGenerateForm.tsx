import { useState } from 'react';
import * as api from '@/lib/api';
import styles from './SummaryGenerateForm.module.css';

interface SummaryGenerateFormProps {
  debateId: string;
  isLoading: boolean;
  onGenerate: (summary: api.SummaryResponse) => void;
  onStatusChange: (status: string) => void;
}

export function SummaryGenerateForm({
  debateId,
  isLoading,
  onGenerate,
  onStatusChange,
}: SummaryGenerateFormProps) {
  const [openrouterKey, setOpenrouterKey] = useState('');
  const [modelId, setModelId] = useState('anthropic/claude-3.5-sonnet');

  const handleGenerate = async () => {
    if (!openrouterKey.trim()) {
      onStatusChange('Error: OpenRouter API key required');
      return;
    }
    
    onStatusChange('Generating summary via OpenRouter...');
    try {
      const result = await api.generateSummary(debateId, {
        openrouter_api_key: openrouterKey,
        model_id: modelId,
      }, openrouterKey);
      onGenerate(result);
      onStatusChange('Summary generated successfully');
    } catch (err: any) {
      onStatusChange(`Error: ${err.message}`);
    }
  };

  return (
    <div className={styles.container}>
      <h3>Generate Meeting Outputs</h3>
      <label>OpenRouter API Key (BYOK)</label>
      <input
        type="password"
        value={openrouterKey}
        onChange={(e) => setOpenrouterKey(e.target.value)}
        placeholder="sk-or-v1-..."
        disabled={isLoading}
      />
      <label>Model ID</label>
      <input
        type="text"
        value={modelId}
        onChange={(e) => setModelId(e.target.value)}
        placeholder="anthropic/claude-3.5-sonnet"
        disabled={isLoading}
      />
      <button
        onClick={handleGenerate}
        disabled={isLoading || !openrouterKey.trim()}
        className={styles.btnPrimary}
      >
        Generate Summary (uses OpenRouter credits)
      </button>
    </div>
  );
}
