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
import { SetupStepper } from '@/components/setup/SetupStepper';
import { useMemoryImport } from '@/hooks/useMemoryImport';
import { useSetupValidation } from '@/hooks/useSetupValidation';
import { useParticipants } from '@/hooks/useParticipants';
import { useMaterials } from '@/hooks/useMaterials';
import { useOpenRouterKey } from '@/hooks/useOpenRouterKey';
import { useDebateSetupActions } from '@/hooks/useDebateSetupActions';
import styles from './setup.module.css';

export default function SetupPage() {
  const router = useRouter();
  const { apiKey } = useOpenRouterKey();
  const [step, setStep] = useState(1);
  const [canEnterRoom, setCanEnterRoom] = useState(false);
  
  // Step 1: Basic Info
  const [title, setTitle] = useState('');
  const [problemStatement, setProblemStatement] = useState('');
  const [agenda, setAgenda] = useState<string[]>([]);
  const [desiredOutcomes, setDesiredOutcomes] = useState<string[]>([]);
  const [timeboxMinutes, setTimeboxMinutes] = useState<number | undefined>(30);
  const [maxRounds, setMaxRounds] = useState<number | undefined>(undefined);

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
    handleReorder: handleReorderParticipant,
  } = useParticipants();
  const [templates, setTemplates] = useState<api.AgentTemplate[]>([]);
  const [agents, setAgents] = useState<api.Agent[]>([]);
  
  // Step 4: Memory Import
  const { memoryImport, setMemoryImport, validateMemoryImport, createMemoryGrants } = useMemoryImport();
  
  // Validation
  const { canGoNext: validateStep } = useSetupValidation();
  
  const workspaceId = '00000000-0000-0000-0000-000000000101';

  // Debate setup actions (create, launch)
  const {
    isLoading,
    createdDebateId,
    createdParticipantIds,
    handleCreateDebate: createDebate,
    handleLaunchDebate,
  } = useDebateSetupActions({
    workspaceId,
    title,
    problemStatement,
    agenda,
    desiredOutcomes,
    timeboxMinutes,
    maxRounds,
    participants,
    materials,
    selectedMemorySources: memoryImport.source_debate_ids,
  });
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
    // Validate memory import
    const memoryError = validateMemoryImport(participants);
    if (memoryError) {
      alert(memoryError);
      return;
    }

    const result = await createDebate();
    if (result) {
      // Create memory grants if enabled
      const shouldContinue = await createMemoryGrants(result.debateId, result.participantIds);
      if (shouldContinue) {
        setStep(5);
      }
    }
  };

  const handleLaunchAfterPreflight = () => {
    if (createdDebateId) {
      handleLaunchDebate(createdDebateId, apiKey);
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

      {!apiKey && (
        <div style={{
          backgroundColor: '#fff3cd',
          border: '1px solid #ffc107',
          borderRadius: '8px',
          padding: '16px 20px',
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <span style={{ fontSize: '24px' }}>⚠️</span>
          <div>
            <strong style={{ color: '#856404' }}>OpenRouter API Key Required</strong>
            <p style={{ margin: '4px 0 0 0', color: '#856404', fontSize: '14px' }}>
              You need to add your OpenRouter API key in <a href="/settings" style={{ color: '#0066cc', textDecoration: 'underline' }}>Settings</a> before launching the meeting. AI agents need this key to participate.
            </p>
          </div>
        </div>
      )}

      <div className={styles.wizard}>
        <SetupStepper steps={steps} currentStep={step} />

        <div className={styles.content}>
          {step === 1 && (
            <BasicInfoStep
              title={title}
              problemStatement={problemStatement}
              agenda={agenda}
              desiredOutcomes={desiredOutcomes}
              timeboxMinutes={timeboxMinutes}
              maxRounds={maxRounds}
              onTitleChange={setTitle}
              onProblemChange={setProblemStatement}
              onAgendaChange={setAgenda}
              onDesiredOutcomesChange={setDesiredOutcomes}
              onTimeboxChange={setTimeboxMinutes}
              onMaxRoundsChange={setMaxRounds}
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
              onReorder={handleReorderParticipant}
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
              onCanContinueChange={setCanEnterRoom}
              meetingTitle={title}
              meetingPurpose={problemStatement}
              meetingAgenda={agenda}
              desiredOutcomes={desiredOutcomes}
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
          {step > 1 && (
            <button 
              onClick={() => {
                // Allow going back to edit earlier steps
                if (step === 5 || step === 6) {
                  // From Preflight/Review, go back to Memory Import
                  setStep(4);
                } else {
                  setStep(step - 1);
                }
              }} 
              disabled={isLoading}
              className={styles.btnPrevious}
            >
              <span className={styles.btnIcon}>←</span>
              <span>Previous</span>
            </button>
          )}
          
          <div style={{ flex: 1 }} />
          
          {step < 4 && (
            <button
              onClick={() => setStep(step + 1)}
              disabled={!canGoNext() || isLoading}
              className={styles.btnNext}
            >
              <span>{isLoading ? 'Loading...' : 'Next'}</span>
              <span className={styles.btnIcon}>→</span>
            </button>
          )}
          
          {step === 4 && (
            <button
              onClick={handleCreateDebate}
              disabled={!canGoNext() || isLoading}
              className={styles.btnNext}
            >
              <span>{isLoading ? 'Creating...' : 'Create & Prepare'}</span>
              <span className={styles.btnIcon}>→</span>
            </button>
          )}
          
          {(step === 5 || step === 6) && (
            <button
              onClick={handleLaunchAfterPreflight}
              disabled={isLoading || !canEnterRoom || !apiKey}
              className={styles.btnLaunch}
              title={!apiKey ? 'Add OpenRouter API key in Settings first' : !canEnterRoom ? 'Complete agent preparation first' : ''}
            >
              <span className={styles.launchIcon}>🚀</span>
              <span>
                {isLoading ? 'Loading...' : !apiKey ? 'API Key Required' : 'Launch Meeting'}
              </span>
            </button>
          )}
        </div>
      </div>
      </div>
    </>
  );
}
