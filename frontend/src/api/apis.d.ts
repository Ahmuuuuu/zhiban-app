export function resolveApiUrl(path: string): string;

export function downloadWithToken(url: string, filename?: string): Promise<void>;

export function login(data: unknown): Promise<unknown>;

export function register(data: unknown): Promise<unknown>;

export function getUserProfile(): Promise<unknown>;

export function updateUserProfile(data: unknown): Promise<unknown>;

export function deleteUser(data: unknown): Promise<unknown>;

export function sendChatMessage(data: unknown): Promise<unknown>;

export function getConversationList(): Promise<unknown>;

export function getConversationMessages(chatGroupId: number | string): Promise<unknown>;

export function streamChatMessage(
  data: {
    user_req: string;
    chat_group_id?: number | string | null;
  },
  handlers?: {
    onChunk?: (chunk: string) => void | Promise<void>;
    onDone?: (data?: { chat_group_id?: number | string }) => void;
    onError?: (error: string) => void;
    onFile?: (fileData: unknown) => void;
  },
): Promise<void>;

export function getPortrait(): Promise<unknown>;

export function getPortraitRadar(): Promise<unknown>;

export function initPortrait(data: unknown): Promise<unknown>;

export function uploadStudyMaterial(data: unknown): Promise<unknown>;

export function getStudyResources(params?: Record<string, unknown>): Promise<unknown>;

export function getStudyStats(): Promise<unknown>;

export function getStudyExamWeekly(): Promise<unknown>;

export function getLearningGuidance(): Promise<unknown>;

export function collectStudyResource(resourceId: number | string): Promise<unknown>;

export function uncollectStudyResource(resourceId: number | string): Promise<unknown>;

export function getStudyCollections(): Promise<unknown>;

export function streamResourceGeneration(
  data: {
    topic: string;
    resource_types: string[];
    chat_group_id?: number | string | null;
  },
  handlers?: {
    onProgress?: (eventData: unknown) => void;
    onDone?: (eventData?: unknown) => void;
    onError?: (error: string) => void;
    onFile?: (eventData: unknown) => void;
  },
): Promise<void>;

export function generateImage(data: {
  prompt: string;
  aspect_ratio?: string;
  img_count?: number;
  chat_group_id?: number | string | null;
}): Promise<unknown>;

export function getImageTaskStatus(taskId: string): Promise<unknown>;

export function getGeneratedImages(): Promise<unknown>;

export function getGeneratedImage(imageId: number | string): Promise<unknown>;

export function deleteGeneratedImage(imageId: number | string): Promise<unknown>;

export function getGeneratedResources(): Promise<unknown>;

export function getGeneratedResource(resourceId: number | string): Promise<unknown>;

export function narrateResource(
  resourceId: number | string,
  options?: {
    voice?: string;
    force_regenerate?: boolean;
  },
): Promise<unknown>;

export function getNarration(narrationId: number | string): Promise<unknown>;

export function getNarrationVoices(): Promise<unknown>;

export function deleteGeneratedResource(resourceId: number | string): Promise<unknown>;

export function getAgentSkills(): Promise<unknown>;

export function getAgentSkill(resourceType: string): Promise<unknown>;

export function upsertAgentSkill(data: {
  resource_type: string;
  name: string;
  system_prompt: string;
}): Promise<unknown>;

export function upsertAgentActionSkill(data: {
  name: string;
  action_type: string;
  action_config: Record<string, unknown>;
  tool_description: string;
}): Promise<unknown>;

export function deleteAgentSkill(resourceType: string): Promise<unknown>;

export function generateExamQuestions(data: {
  topic: string;
  count?: number;
  difficulty?: string;
  question_types?: string;
}): Promise<unknown>;

export function getExamQuestions(params?: Record<string, unknown>): Promise<unknown>;

export function getExamQuestion(questionId: number | string): Promise<unknown>;

export function submitExamAnswer(data: {
  question_id: number | string;
  answer: string;
  time_spent?: number | null;
  session_id?: string | null;
}): Promise<unknown>;

export function getExamSession(sessionId: string): Promise<unknown>;

export function getExamSessions(): Promise<unknown>;

export function getCurrentLearningPath(): Promise<unknown>;

export function completeLearningPathNode(nodeId: number | string, sessionId: string): Promise<unknown>;

export function generateLearningPath(data: {
  subject: string;
  difficulty?: string;
  node_count?: number;
}): Promise<unknown>;

export function getLearningPaths(): Promise<unknown>;

export function getLearningPathDetail(pathId: number | string): Promise<unknown>;

export function getLearningPathProgress(pathId: number | string): Promise<unknown>;

export function enrollLearningPath(pathId: number | string): Promise<unknown>;

export function generatePathNodeResources(pathId: number | string, nodeId: number | string): Promise<unknown>;

export function generatePathNodeQuiz(pathId: number | string, nodeId: number | string): Promise<unknown>;
