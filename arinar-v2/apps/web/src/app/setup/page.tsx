'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import AppNav from '@/components/layout/AppNav';
import * as api from '@/lib/api';
import { BasicInfoStep } from '@/components/setup/BasicInfoStep';
import { MaterialsStep } from '@/components/setup/MaterialsStep';
import { ParticipantsStep } from '@/components/setup/ParticipantsStep';
import { ReviewStep } from '@/components/setup/ReviewStep';
import styles from './setup.module.css';

export default function SetupPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  
  // Step 1: Basic Info
  const [title, setTitle] = useState('');
  const [problemStatement, setProblemStatement] = useState('');
  const [timeboxMinutes, setTimeboxMinutes] = useState<number | undefined>(30);
  
  // Step 2: Materials
  const [materials, setMaterials] = useState<api.SetupMaterial[]>([]);
  
  // Step 3: Participants
  const [participants, setParticipants] = useState<api.SetupParticipant[]>([]);
  const [templates, setTemplates] = useState<api.AgentTemplate[]>([]);
  const [agents, setAgents] = useState<api.Agent[]>([]);
  
  const workspaceId = '00000000-0000-0000-0000-000000000101';

  useEffect(() => {
    const loadData = async () => {
      try {
        const [templatesData, agentsData] = await Promise.all([
          api.listAgentTemplates(),
          api.listAgents(workspaceId),
        ]);
        setTemplates(templatesData);
        setAgents(agentsData);
      } catch (err: any) {
        console.error('Failed to load templates/agents:', err);
      }
    };
    loadData();
  }, []);

  const handleAddMaterial = (kind: 'text' | 'link' | 'file_placeholder') => {
    setMaterials([...materials, { kind, title: '', body_text: '', url: '' }]);
  };

  const handleUpdateMaterial = (idx: number, updates: Partial<api.SetupMaterial>) => {
    const updated = [...materials];
    updated[idx] = { ...updated[idx], ...updates };
    setMaterials(updated);
  };

  const handleRemoveMaterial = (idx: number) => {
    setMaterials(materials.filter((_, i) => i !== idx));
  };

  const handleAddParticipantFromTemplate = (template: api.AgentTemplate) => {
    if (participants.length >= 8) {
      alert('Maximum 8 participants allowed');
      return;
    }
    
    setParticipants([...participants, {
      name: template.label,
      role_description: template.role_title,
      system_prompt: template.system_prompt,
      model_id: template.model_id,
      model_config: template.model_config,
    }]);
  };

  const handleAddExistingAgent = (agent: api.Agent) => {
    if (participants.length >= 8) {
      alert('Maximum 8 participants allowed');
      return;
    }
    
    setParticipants([...participants, { agent_id: agent.agent_id }]);
  };

  const handleUpdateParticipant = (idx: number, updates: Partial<api.SetupParticipant>) => {
    const updated = [...participants];
    updated[idx] = { ...updated[idx], ...updates };
    setParticipants(updated);
  };

  const handleRemoveParticipant = (idx: number) => {
    setParticipants(participants.filter((_, i) => i !== idx));
  };

  const handleLaunch = async () => {
    if (participants.length === 0) {
      alert('At least 1 participant required');
      return;
    }
    
    setIsLoading(true);
    try {
      const result = await api.setupDebate({
        workspace_id: workspaceId,
        title,
        problem_statement: problemStatement,
        timebox_minutes: timeboxMinutes,
        participants,
        materials,
      });
      
      router.push(`/operator?debate_id=${result.debate_id}`);
    } catch (err: any) {
      alert(`Failed to create debate: ${err.message}`);
      setIsLoading(false);
    }
  };

  const canGoNext = () => {
    if (step === 1) return title.trim() && problemStatement.trim();
    if (step === 3) return participants.length > 0;
    return true;
  };

  return (
    <>
      <AppNav />
      <div className={styles.container}>
      <header className={styles.header}>
        <h1>Meeting Setup</h1>
        <p className={styles.subtitle}>Configure your AI-moderated discussion</p>
      </header>

      <div className={styles.wizard}>
        <div className={styles.steps}>
          <div className={`${styles.step} ${step === 1 ? styles.stepActive : ''} ${step > 1 ? styles.stepCompleted : ''}`}>
            <div className={styles.stepNumber}>{step > 1 ? '✓' : '1'}</div>
            <div className={styles.stepLabel}>Basic Info</div>
          </div>
          <div className={`${styles.step} ${step === 2 ? styles.stepActive : ''} ${step > 2 ? styles.stepCompleted : ''}`}>
            <div className={styles.stepNumber}>{step > 2 ? '✓' : '2'}</div>
            <div className={styles.stepLabel}>Materials</div>
          </div>
          <div className={`${styles.step} ${step === 3 ? styles.stepActive : ''} ${step > 3 ? styles.stepCompleted : ''}`}>
            <div className={styles.stepNumber}>{step > 3 ? '✓' : '3'}</div>
            <div className={styles.stepLabel}>Participants</div>
          </div>
          <div className={`${styles.step} ${step === 4 ? styles.stepActive : ''}`}>
            <div className={styles.stepNumber}>4</div>
            <div className={styles.stepLabel}>Review</div>
          </div>
        </div>

        <div className={styles.content}>
          {step === 1 && (
            <BasicInfoStep
              title={title}
              problemStatement={problemStatement}
              timeboxMinutes={timeboxMinutes}
              onTitleChange={setTitle}
              onProblemChange={setProblemStatement}
              onTimeboxChange={setTimeboxMinutes}
              isLoading={isLoading}
            />
          )}

          {step === 2 && (
            <MaterialsStep
              materials={materials}
              onAdd={handleAddMaterial}
              onUpdate={handleUpdateMaterial}
              onRemove={handleRemoveMaterial}
            />
          )}

          {step === 3 && (
            <ParticipantsStep
              participants={participants}
              templates={templates}
              agents={agents}
              onAddFromTemplate={handleAddParticipantFromTemplate}
              onAddExisting={handleAddExistingAgent}
              onUpdate={handleUpdateParticipant}
              onRemove={handleRemoveParticipant}
            />
          )}

          {step === 4 && (
            <ReviewStep
              title={title}
              problemStatement={problemStatement}
              timeboxMinutes={timeboxMinutes}
              materials={materials}
              participants={participants}
              workspaceId={workspaceId}
            />
          )}
        </div>

        <div className={styles.actions}>
          <div>
            {step > 1 && (
              <button onClick={() => setStep(step - 1)} disabled={isLoading}>
                ← Previous
              </button>
            )}
          </div>
          
          <div>
            {step < 4 && (
              <button
                onClick={() => setStep(step + 1)}
                disabled={!canGoNext() || isLoading}
              >
                {isLoading ? 'Loading...' : 'Next'}
              </button>
            )}
            
            {step === 4 && (
              <button
                onClick={handleLaunch}
                disabled={isLoading}
              >
                {isLoading ? 'Creating...' : 'Create Meeting'}
              </button>
            )}
          </div>
        </div>
      </div>
      </div>
    </>
  );
}
