export function resolveApiUrl(path: string): string;

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

export function initPortrait(data: unknown): Promise<unknown>;

export function uploadStudyMaterial(data: unknown): Promise<unknown>;

export function getStudyResources(params?: Record<string, unknown>): Promise<unknown>;

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

export function deleteGeneratedResource(resourceId: number | string): Promise<unknown>;
