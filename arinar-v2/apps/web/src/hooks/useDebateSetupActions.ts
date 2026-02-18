/**
 * Hook for debate setup actions (create, launch)
 * Extracted from setup/page.tsx for maintainability
 */
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import * as api from '@/lib/api';
import type { SetupParticipant, SetupMaterial } from '@/lib/api';
import { getAccessToken } from '@/lib/supabase';

interface UseDebateSetupActionsOptions {
  workspaceId: string;
  title: string;
  problemStatement: string;
  agenda?: string[];
  desiredOutcomes?: string[];
  timeboxMinutes?: number;
  maxRounds?: number;
  enableHost?: boolean;
  hostModelId?: string;
  yoloMode?: boolean;
  autoTurnDelay?: number;
  enableDocuments?: boolean;
  documentTemplateId?: string;
  documentTitle?: string;
  participants: SetupParticipant[];
  materials: SetupMaterial[];
  selectedMemorySources: string[];
}

interface UseDebateSetupActionsReturn {
  isLoading: boolean;
  createdDebateId: string | null;
  createdParticipantIds: string[];
  setCreatedParticipantIds: (ids: string[]) => void;
  handleCreateDebate: () => Promise<{ debateId: string; participantIds: string[] } | null>;
  handleLaunchDebate: (debateId: string, apiKey: string | null) => Promise<void>;
}

export function useDebateSetupActions(
  options: UseDebateSetupActionsOptions
): UseDebateSetupActionsReturn {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [createdDebateId, setCreatedDebateId] = useState<string | null>(null);
  const [createdParticipantIds, setCreatedParticipantIds] = useState<string[]>([]);

  const handleCreateDebate = async () => {
    const {
      workspaceId,
      title,
      problemStatement,
      agenda,
      desiredOutcomes,
      timeboxMinutes,
      maxRounds,
      enableHost,
      hostModelId,
      yoloMode,
      autoTurnDelay,
      participants,
      materials,
      selectedMemorySources,
    } = options;

    // Allow creating debate without participants initially (for file uploads)
    // Validation happens later at preflight
    setIsLoading(true);
    try {
      // 1. Create debate (returns participant_ids)
      // Host is NOT a participant - it's stored in policy_config
      const setupResponse = await api.setupDebate({
        workspace_id: workspaceId,
        title,
        problem_statement: problemStatement,
        agenda: agenda && agenda.length > 0 ? agenda : undefined,
        desired_outcomes: desiredOutcomes && desiredOutcomes.length > 0 ? desiredOutcomes : undefined,
        timebox_minutes: timeboxMinutes || 30,
        max_rounds: maxRounds,
        enable_host: enableHost || false,
        host_model_id: enableHost ? (hostModelId || 'openai/gpt-4o-mini') : undefined,
        participants: participants,
        materials: materials && materials.length > 0 ? materials : undefined,
      });

      const { debate_id, participant_ids } = setupResponse;
      setCreatedDebateId(debate_id);
      setCreatedParticipantIds(participant_ids);

      // 2. Import memory if selected
      if (selectedMemorySources && selectedMemorySources.length > 0) {
        try {
          await api.importMemory(debate_id, {
            source_debate_ids: selectedMemorySources,
            participant_ids: participant_ids,
          });
          console.log('Memory imported successfully');
        } catch (memErr: any) {
          console.error('Memory import failed:', memErr);
          alert(`Warning: Memory import failed: ${memErr.message}. Continuing with debate creation.`);
        }
      }

      // 3. Create document if enabled
      if (options.enableDocuments) {
        try {
          const { getAllTemplates } = await import('@/lib/document/templates');
          const templates = getAllTemplates();
          const selectedTemplate = templates.find(t => t.id === options.documentTemplateId);
          
          if (selectedTemplate) {
            const docTitle = options.documentTitle || `${title} - ${selectedTemplate.title}`;
            await api.createDocument({
              debate_id: debate_id,
              template_id: options.documentTemplateId || 'meeting-summary',
              title: docTitle,
              custom_sections: selectedTemplate.sections,
            });
            console.log('✅ Document created successfully');
          }
        } catch (docErr: any) {
          console.error('Document creation failed:', docErr);
          alert(`Warning: Document creation failed: ${docErr.message}. Continuing with debate.`);
        }
      }

      return { debateId: debate_id, participantIds: participant_ids };
    } catch (err: any) {
      alert(`Failed to create debate: ${err.message}`);
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const handleLaunchDebate = async (debateId: string, apiKey: string | null) => {
    // Validate auth token before launching (required for WebSocket connection)
    try {
      const authToken = await getAccessToken();
      if (!authToken) {
        alert(
          '⚠️ Authentication Required\n\nNo auth token available. This should not happen in development mode.\n\nPlease check your .env.local file has NEXT_PUBLIC_AUTH_MODE=development and NEXT_PUBLIC_TEST_TOKEN configured.'
        );
        return;
      }
    } catch (err: any) {
      alert(`⚠️ Authentication Error\n\nFailed to get auth token: ${err.message}`);
      return;
    }

    // Validate API key before launching
    if (!apiKey) {
      alert(
        '⚠️ OpenRouter API Key Required\n\nYou need to add your OpenRouter API key in Settings before starting the debate.\n\nThe AI agents need this key to participate in the discussion.'
      );
      return;
    }

    // Test API key validity by making a quick validation call
    try {
      await api.getOpenRouterAccount(apiKey);
    } catch (err: any) {
      alert(
        `⚠️ Invalid OpenRouter API Key\n\nYour API key failed validation: ${err.message}\n\nPlease update your API key in Settings before launching the debate.`
      );
      return;
    }

    if (!debateId) {
      alert('No debate created yet. Please complete the setup first.');
      return;
    }

    setIsLoading(true);

    try {
      // Start the debate (pending -> running)
      await api.startDebate(debateId);

      // Check if YOLO mode is enabled
      if (options.yoloMode) {
        // Start autonomous mode
        if (!apiKey) {
          throw new Error('OpenRouter API key required for YOLO mode. Please add it in Settings.');
        }
        await api.startAutonomousDebate(debateId, options.autoTurnDelay || 10, apiKey);
        console.log('🚀 YOLO Mode activated!');
      } else {
        // Trigger first agent turn immediately (manual mode)
        await api.triggerNextTurn(debateId, apiKey);
      }

      // Navigate to room
      router.push(`/room?debate_id=${debateId}`);
    } catch (err: any) {
      console.error('Failed to start debate:', err);
      alert(`Failed to start debate: ${err.message || 'Unknown error'}`);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    isLoading,
    createdDebateId,
    createdParticipantIds,
    setCreatedParticipantIds,
    handleCreateDebate,
    handleLaunchDebate,
  };
}
