export {
  API_BASE_URL,
  downloadWithToken,
  normalizeAvatarUrl,
  parseStreamEvent,
  resolveApiUrl,
  requestFirstAvailable
} from './config'

export {
  isBackendUnavailableError
} from './request'

export {
  login,
  register,
  registerByEmail,
  sendEmailCode
} from './auth'

export {
  deleteUser,
  deleteUserAvatar,
  getUserProfile,
  updateUserProfile,
  uploadUserAvatar
} from './user'

export {
  deleteConversation,
  getConversationList,
  getConversationMessages,
  sendChatMessage,
  streamChatMessage,
  transcribeVoiceInput
} from './chat'

export {
  getNextPortraitInterviewQuestion,
  getPortrait,
  getPortraitRadar,
  initPortrait,
  initPortraitFromDialogue
} from './portrait'

export {
  collectStudyResource,
  deleteStudyResource,
  getLearningGuidance,
  getStudyCollections,
  getStudyExamWeekly,
  getStudyPathStats,
  getStudyResources,
  getStudyStats,
  markStudyResourceRead,
  markStudyResourceUnread,
  sendStudyHeartbeat,
  uncollectStudyResource,
  uploadStudyMaterial
} from './study'

export {
  createResourceAnnotation,
  createResourceGenerationTask,
  deleteGeneratedResource,
  deleteResourceAnnotation,
  exportEditedPptx,
  favoriteResource,
  getGeneratedResource,
  getGeneratedResources,
  getResourceAnnotations,
  getResourceGenerationTask,
  getResourceGenerationTasks,
  likeResource,
  publishGeneratedResource,
  streamResourceGenerationTask,
  streamResourceGeneration,
  unfavoriteResource,
  unlikeResource,
  updateResourceAnnotation
} from './resource'

export {
  getNarration,
  getNarrationVoices,
  narrateResource
} from './video'

export {
  generatePresentation,
  getPresentation,
  getPresentationQuestions,
  getPresentations,
  previewPresentation,
  streamPresentationProgress
} from './presentation'

export {
  deleteGeneratedImage,
  generateImage,
  getGeneratedImage,
  getGeneratedImages,
  getImageTaskStatus,
  publishGeneratedImage
} from './image'

export {
  approvePublicResourceApplication,
  deleteAdminResource,
  getAdminKnowledgeBase,
  getAdminPendingResources,
  getAdminResources,
  getAdminUsers,
  importAdminBaseResource,
  rejectPublicResourceApplication,
  updateAdminResource
} from './admin'

export {
  deleteAgentSkill,
  getAgentSkill,
  getAgentSkills,
  upsertAgentActionSkill,
  upsertAgentSkill
} from './agent'

export {
  generateExamQuestions,
  getExamQuestion,
  getExamQuestions,
  getExamSession,
  getExamSessions,
  submitExamAnswer
} from './exam'

export {
  completeLearningPathNode,
  enrollLearningPath,
  generateLearningPath,
  generateLearningPathStream,
  generateLearningPathsFromProfile,
  generatePathNodeQuiz,
  generatePathNodeResources,
  generatePathNodeResourcesStream,
  getCurrentLearningPath,
  getLearningPathDetail,
  getLearningPathProgress,
  getLearningPaths
} from './learningPath'

export {
  getNotifications,
  getUnreadNotificationCount,
  markAllNotificationsRead,
  markNotificationRead
} from './notification'
