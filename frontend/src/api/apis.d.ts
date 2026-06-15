export function resolveApiUrl(path: string): string;

export function normalizeAvatarUrl(avatar: string | null | undefined): string;

export function downloadWithToken(url: string, filename?: string): Promise<void>;

export function login(data: unknown): Promise<unknown>;

export function register(data: unknown): Promise<unknown>;

export function sendEmailCode(data: { email: string; purpose?: 'login' | 'register' | 'bind' | string }): Promise<unknown>;

export function registerByEmail(data: {
  username: string;
  email: string;
  password: string;
  code: string;
}): Promise<unknown>;

export function getUserProfile(): Promise<unknown>;

export function updateUserProfile(data: unknown): Promise<unknown>;

export function uploadUserAvatar(file: File): Promise<unknown>;

export function deleteUserAvatar(): Promise<unknown>;

export function deleteUser(data: unknown): Promise<unknown>;

export function sendChatMessage(data: unknown): Promise<unknown>;

export function getConversationList(): Promise<unknown>;

export function getConversationMessages(chatGroupId: number | string): Promise<unknown>;

export function deleteConversation(chatGroupId: number | string): Promise<unknown>;

export function transcribeVoiceInput(audioBlob: Blob): Promise<unknown>;

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

export function deleteStudyResource(resourceId: number | string): Promise<unknown>;

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

export function getGeneratedImages(params?: Record<string, unknown>): Promise<unknown>;

export function getGeneratedImage(imageId: number | string): Promise<unknown>;

export function deleteGeneratedImage(imageId: number | string): Promise<unknown>;

export function publishGeneratedImage(imageId: number | string, visibility?: 'public' | 'private' | string): Promise<unknown>;

export function getGeneratedResources(params?: Record<string, unknown>): Promise<unknown>;

export function getGeneratedResource(resourceId: number | string): Promise<unknown>;

export function getResourceAnnotations(
  sourceId: number | string,
  sourceType?: string,
): Promise<unknown>;

export function createResourceAnnotation(
  resourceId: number | string,
  data: Record<string, unknown>,
): Promise<unknown>;

export function updateResourceAnnotation(
  resourceId: number | string,
  annotationId: number | string,
  data: Record<string, unknown>,
): Promise<unknown>;

export function deleteResourceAnnotation(
  resourceId: number | string,
  annotationId: number | string,
): Promise<unknown>;

export function exportEditedPptx(
  resourceId: number | string,
  data?: {
    title?: string;
    filename?: string;
    slides?: Array<Record<string, unknown>>;
  },
): Promise<void>;

export function createResourceGenerationTask(data: {
  topic: string;
  resource_types: string[];
  chat_group_id?: number | string | null;
}): Promise<unknown>;

export function getResourceGenerationTask(taskId: number | string): Promise<unknown>;

export function getResourceGenerationTasks(): Promise<unknown>;

export function likeResource(resourceId: number | string): Promise<unknown>;

export function unlikeResource(resourceId: number | string): Promise<unknown>;

export function favoriteResource(resourceId: number | string): Promise<unknown>;

export function unfavoriteResource(resourceId: number | string): Promise<unknown>;

export function narrateResource(
  resourceId: number | string,
  options?: {
    voice?: string;
    force_regenerate?: boolean;
  },
): Promise<unknown>;

export function getNarration(narrationId: number | string): Promise<unknown>;

export function getNarrationVoices(): Promise<unknown>;

export function getPresentationQuestions(data: {
  topic: string;
  chat_group_id?: number;
}): Promise<unknown>;

export function generatePresentation(data: {
  topic: string;
  voice?: string;
  chapters?: string[];
  answers?: Record<string, unknown>;
  chat_group_id?: number;
  video_mode?: boolean;
}): Promise<unknown>;

export function previewPresentation(data: { topic: string }): Promise<unknown>;

export function getPresentations(): Promise<unknown>;

export function getPresentation(presentationId: number | string): Promise<unknown>;

export function deleteGeneratedResource(resourceId: number | string): Promise<unknown>;

export function publishGeneratedResource(resourceId: number | string, visibility?: 'public' | 'private' | string): Promise<unknown>;

export function getAdminUsers(): Promise<unknown>;

export function getAdminKnowledgeBase(): Promise<unknown>;

export function getAdminPendingResources(params?: Record<string, unknown>): Promise<unknown>;

export function getAdminResources(params?: Record<string, unknown>): Promise<unknown>;

export function approvePublicResourceApplication(
  applicationId: number | string,
  data?: Record<string, unknown>,
): Promise<unknown>;

export function rejectPublicResourceApplication(
  applicationId: number | string,
  data?: Record<string, unknown>,
): Promise<unknown>;

export function updateAdminResource(
  resourceId: number | string,
  data?: Record<string, unknown>,
): Promise<unknown>;

export function deleteAdminResource(resourceId: number | string): Promise<unknown>;

export function importAdminBaseResource(data: FormData | Record<string, unknown>): Promise<unknown>;

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

export function getStudyPathStats(): Promise<unknown>;

export function sendStudyHeartbeat(pathId?: number | string | null): Promise<unknown>;

export function markStudyResourceRead(resourceId: number | string, durationSeconds?: number): Promise<unknown>;

export function markStudyResourceUnread(resourceId: number | string): Promise<unknown>;

export function completeLearningPathNode(nodeId: number | string, sessionId: string): Promise<unknown>;

export function generateLearningPath(data: {
  subject: string;
  difficulty?: string;
  node_count?: number;
}): Promise<unknown>;

export function generateLearningPathsFromProfile(data?: {
  difficulty?: string;
  node_count?: number;
  course_limit?: number;
}): Promise<unknown>;

export function getLearningPaths(): Promise<unknown>;

export function getLearningPathDetail(pathId: number | string): Promise<unknown>;

export function getLearningPathProgress(pathId: number | string): Promise<unknown>;

export function enrollLearningPath(pathId: number | string): Promise<unknown>;

export function generatePathNodeResources(pathId: number | string, nodeId: number | string): Promise<unknown>;

export function generatePathNodeQuiz(pathId: number | string, nodeId: number | string): Promise<unknown>;
