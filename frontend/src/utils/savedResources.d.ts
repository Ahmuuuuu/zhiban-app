export const SAVED_GENERATED_RESOURCES_KEY: string;

export interface SavedResourceRef {
  id: string;
  sourceId: string;
  kind: string;
  fileType: string;
  category: string;
  quizId: string;
  title: string;
  filename: string;
  content: string;
  coverUrl: string;
  previewUrl: string;
  downloadUrl: string;
  annotations: Array<Record<string, unknown>>;
  visibility: string;
  createdAt: string;
}

export interface SaveGeneratedResourcePayload {
  sourceId?: string | number;
  kind?: string;
  fileType?: string;
  category?: string;
  quizId?: string;
  title?: string;
  filename?: string;
  content?: string;
  coverUrl?: string;
  previewUrl?: string;
  downloadUrl?: string;
  annotations?: Array<Record<string, unknown>>;
  visibility?: string;
}

export function readSavedResourceRefs(visibility?: string): SavedResourceRef[];

export function saveGeneratedResourceRef(payload: SaveGeneratedResourcePayload): SavedResourceRef;

export function hydrateSavedResourceRefs(visibility?: string): Promise<unknown[]>;
