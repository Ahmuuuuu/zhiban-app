import { createRouter, createWebHashHistory } from 'vue-router'

import HomeView from '../pages/HomeView.vue'
import ResourceView from '../pages/ResourceView.vue'
import ResourceCenterView from '../pages/ResourceCenterView.vue'
import ChatView from '../pages/ChatView.vue'
import StudyPath from '../pages/StudyPath.vue'
import StudySituation from '../pages/StudySituation.vue'
import StudyImportView from '../pages/StudyImportView.vue'
import MyStudyView from '../pages/MyStudyView.vue'
import MyProfile from '../pages/MyAccount/MyProfile.vue'
import QuizRunnerView from '../pages/QuizRunnerView.vue'
import PresentationPlayerView from '../pages/PresentationPlayerView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/resources',
      name: 'resources',
      component: ResourceCenterView
    },
    {
      path: '/chat',
      name: 'chat',
      component: ChatView
    },
    {
      path: '/presentation-player',
      name: 'presentationPlayer',
      component: PresentationPlayerView
    },
    {
      path: '/question-bank',
      name: 'questionBank',
      redirect: {
        path: '/learning-resources',
        query: { category: 'quiz' }
      }
    },
    {
      path: '/question-bank/:quizId',
      name: 'quizRunner',
      component: QuizRunnerView
    },
    {
      path: '/spath',
      redirect: '/learning-path'
    },
    {
      path: '/situation',
      redirect: '/learning-situation'
    },
    {
      path: '/learning-resources',
      name: 'learningResources',
      component: ResourceView
    },
    {
      path: '/learning-path',
      name: 'learningPath',
      component: StudyPath
    },
    {
      path: '/learning-situation',
      name: 'learningSituation',
      component: StudySituation
    },
    {
      path: '/mine',
      component: MyStudyView,
      redirect: '/learning-resources',
      children: [
        {
          path: 'resources',
          redirect: '/learning-resources'
        },
        {
          path: 'situation',
          redirect: '/learning-situation'
        },
        {
          path: 'path',
          redirect: '/learning-path'
        }
      ]
    },
    {
      path: '/study-import',
      name: 'studyImport',
      component: StudyImportView
    },
    {
      path: '/profile',
      name: 'profile',
      component: MyProfile
    }
  ]
})

export default router
