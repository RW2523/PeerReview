'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import AppNav from '@/components/layout/AppNav';
import * as api from '@/lib/api';
import { BasicInfoStep } from '@/components/setup/BasicInfoStep';
import { MaterialsStep } from '@/components/setup/MaterialsStep';
import { ParticipantsStep } from '@/components/setup/ParticipantsStep';
import { MemoryImportStep } from '@/components/setup/MemoryImportStep';
import { PreflightStep } from '@/components/setup/PreflightStep';
import { ReviewStep } from '@/components/setup/ReviewStep';
import { useMemoryImport } from '@/hooks/useMemoryImport';
import { useSetupValidation } from '@/hooks/useSetupValidation';
import { useParticipants } from '@/hooks/useParticipants';
import { useMaterials } from '@/hooks/useMaterials';
import styles from './setup.module.css';

export default function SetupPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  
  // Debate creation tracking
  const [createdDebateId, setCreatedDebateId] = useState<string | null>(null);
  const [createdParticipantIds, setCreatedParticipantIds] = useState<string[]>([]);
  const [canEnterRoom, setCanEnterRoom] = useState(false);
  
  // Step 1: Basic Info
  const [title, setTitle] = useState('');
  const [problemStatement, setProblemStatement] = useState('');
  const [timeboxMinutes, setTimeboxMinutes] = useState<number | undefined>(30);

  // Pre-fill from draft if coming from home page
  useEffect(() => {
    const draft = sessionStorage.getItem('debate_draft');
    if (draft) {
      try {
        const data = JSON.parse(draft);
        setTitle(data.title || '');
        setProblemStatement(data.problemStatement || '');
        sessionStorage.removeItem('debate_draft');
      } catch (e) {
        console.error('Failed to parse debate draft:', e);
      }
    }
  }, []);
  
  // Step 2: Materials
  const {
    materials,
    handleAdd: handleAddMaterial,
    handleUpdate: handleUpdateMaterial,
    handleRemove: handleRemoveMaterial,
  } = useMaterials();
  
  // Step 3: Participants
  const {
    participants,
    setParticipants,
    handleAddFromTemplate: handleAddParticipantFromTemplate,
    handleAddExisting: handleAddExistingAgent,
    handleUpdate: handleUpdateParticipant,
    handleRemove: handleRemoveParticipant,
  } = useParticipants();
  const [templates, setTemplates] = useState<api.AgentTemplate[]>([]);
  const [agents, setAgents] = useState<api.Agent[]>([]);
  
  // Step 4: Memory Import
  const { memoryImport, setMemoryImport, validateMemoryImport, createMemoryGrants } = useMemoryImport();
  
  // Validation
  const { canGoNext: validateStep } = useSetupValidation();
  
  const workspaceId = '00000000-0000-0000-0000-000000000101';
  const steps = [
    { id: 1, label: 'Basic Info' },
    { id: 2, label: 'Materials' },
    { id: 3, label: 'Participants' },
    { id: 4, label: 'Memory' },
    { id: 5, label: 'Prepare' },
    { id: 6, label: 'Review' },
  ];

  useEffect(() => {
    const loadData = async () => {
      try {
        console.log('Loading templates and agents...');
        const [templatesData, agentsData] = await Promise.all([
          api.listAgentTemplates(),
          api.listAgents(workspaceId),
        ]);
        console.log('Templates loaded:', templatesData.length);
        console.log('Agents loaded:', agentsData.length);
        setTemplates(templatesData);
        setAgents(agentsData);
      } catch (err: any) {
        console.error('Failed to load templates/agents:', err);
        alert(`Failed to load templates/agents: ${err.message}`);
      }
    };
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreateDebate = async () => {
    if (participants.length === 0) {
      alert('At least 1 participant required');
      return;
    }
    
    // Validate memory import
    const memoryError = validateMemoryImport(participants);
    if (memoryError) {
      alert(memoryError);
      return;
    }
    
    setIsLoading(true);
    try {
      // 1. Create debate (returns participant_ids)
      const result = await api.setupDebate({
        workspace_id: workspaceId,
        title,
        problem_statement: problemStatement,
        timebox_minutes: timeboxMinutes,
        participants,
        materials,
      });
      
      // 2. Create memory grants if enabled (pass participant_ids for mapping)
      const shouldContinue = await createMemoryGrants(result.debate_id, result.participant_ids);
      if (!shouldContinue) {
        setIsLoading(false);
        return;
      }
      
      // 3. Store debate_id and participant_ids, move to preflight step
      setCreatedDebateId(result.debate_id);
      setCreatedParticipantIds(result.participant_ids);
      setStep(5); // Move to preflight
      setIsLoading(false);
    } catch (err: any) {
      alert(`Failed to create debate: ${err.message}`);
      setIsLoading(false);
    }
  };

  const handleLaunchAfterPreflight = () => {
    if (createdDebateId) {
      router.push(`/room?debate_id=${createdDebateId}`);
    }
  };

  const canGoNext = () => validateStep(step, title, problemStatement, participants);

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
          <div className={`${styles.step} ${step === 4 ? styles.stepActive : ''} ${step > 4 ? styles.stepCompleted : ''}`}>
            <div className={styles.stepNumber}>{step > 4 ? '✓' : '4'}</div>
            <div className={styles.stepLabel}>Memory</div>
          </div>
          <div className={`${styles.step} ${step === 5 ? styles.stepActive : ''} ${step > 5 ? styles.stepCompleted : ''}`}>
            <div className={styles.stepNumber}>{step > 5 ? '✓' : '5'}</div>
            <div className={styles.stepLabel}>Prepare</div>
          </div>
          <div className={`${styles.step} ${step === 6 ? styles.stepActive : ''}`}>
            <div className={styles.stepNumber}>6</div>
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
            <MemoryImportStep
              workspaceId={workspaceId}
              participants={participants}
              memoryImport={memoryImport}
              onUpdate={setMemoryImport}
            />
          )}

          {step === 5 && (
            <PreflightStep
              debateId={createdDebateId}
              participants={participants}
              participantIds={createdParticipantIds}
            />
          )}

          {step === 6 && (
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

        <div className={styles.navigation}>
          {step > 1 && step !== 5 && (
            <button 
              onClick={() => setStep(step - 1)} 
              disabled={isLoading}
              className={styles.btnSecondary}
            >
              ← Previous
            </button>
          )}
          
          <div style={{ flex: 1 }} />
          
          {step < 4 && (
            <button
              onClick={() => setStep(step + 1)}
              disabled={!canGoNext() || isLoading}
              className={styles.btnPrimary}
            >
              {isLoading ? 'Loading...' : 'Next →'}
            </button>
          )}
          
          {step === 4 && (
            <button
              onClick={handleCreateDebate}
              disabled={!canGoNext() || isLoading}
              className={styles.btnPrimary}
            >
              {isLoading ? 'Creating...' : 'Create & Prepare →'}
            </button>
          )}
          
          {step === 5 && (
            <button
              onClick={handleLaunchAfterPreflight}
              disabled={isLoading}
              className={styles.btnLaunch}
            >
              {isLoading ? 'Loading...' : 'Enter Room'}
            </button>
          )}
          
          {step === 6 && (
            <button
              onClick={handleLaunchAfterPreflight}
              disabled={isLoading}
              className={styles.btnLaunch}
            >
              {isLoading ? 'Loading...' : 'Enter Room'}
            </button>
          )}
        </div>
      </div>
      </div>
    </>
  );
}
