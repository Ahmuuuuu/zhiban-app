export {
  API_BASE_URL,
  downloadWithToken,
  normalizeAvatarUrl,
  parseStreamEvent,
  resolveApiUrl,
  requestFirstAvailable
} from './config'

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
  getConversationList,
  getConversationMessages,
  sendChatMessage,
  streamChatMessage
} from './chat'

export {
  getPortrait,
  getPortraitRadar,
  initPortrait
} from './portrait'

export {
  collectStudyResource,
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
  previewPresentation
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
