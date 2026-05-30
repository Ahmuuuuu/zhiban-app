<template>
  <TopNav />

  <div class="slide-stage">
    <!-- Current page -->
    <div
      class="slide-pane"
      :class="{ moving: isSliding }"
      :style="{ transform: `translate3d(${currentX}%, 0, 0)` }"
    >
      <component :is="currentPane?.component" v-if="currentPane" />
    </div>

    <!-- Next page (only rendered during transition) -->
    <div
      v-if="nextPane"
      class="slide-pane"
      :class="{ moving: isSliding }"
      :style="{ transform: `translate3d(${nextX}%, 0, 0)` }"
    >
      <component :is="nextPane.component" />
    </div>
  </div>

  <StudyPet floating auto-play-actions />
</template>

<script setup>
import { ref, watch, nextTick, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TopNav from './components/TopNav.vue'
import StudyPet from './components/StudyPet.vue'

const route = useRoute()
const router = useRouter()

// ---- route-name → component map ----
const compByRouteName = Object.create(null)
router.getRoutes().forEach(r => {
  if (r.name && r.components?.default) compByRouteName[r.name] = r.components.default
})

function resolveComponent(targetRoute) {
  if (!targetRoute) return null
  if (targetRoute.name && compByRouteName[targetRoute.name]) return compByRouteName[targetRoute.name]
  const m = targetRoute.matched
  if (m?.length) {
    for (let i = m.length - 1; i >= 0; i--) {
      if (m[i].components?.default) return m[i].components.default
    }
  }
  return null
}

// ---- nav order for slide direction ----
const navOrder = ['/', '/chat', '/learning-resources', '/learning-path', '/learning-situation']
function navIndex(p) {
  const i = navOrder.indexOf(p)
  if (i !== -1) return i
  for (let j = navOrder.length - 1; j >= 0; j--) {
    if (p.startsWith(navOrder[j])) return j
  }
  return -1
}

// ---- animation state ----
const currentPane = shallowRef(null)  // { key, component }
const nextPane = shallowRef(null)
const currentX = ref(0)
const nextX = ref(100)
const isSliding = ref(false)

let lastPath = null
let locked = false

const DURATION = 550  // ms, must match CSS

async function animate(fromPath, toPath) {
  if (locked) return
  locked = true

  const comp = resolveComponent(route)
  if (!comp) { locked = false; return }

  const key = toPath + '::' + Date.now()

  // First visit — no animation
  if (!currentPane.value) {
    currentPane.value = { key, component: comp }
    lastPath = toPath
    locked = false
    return
  }

  const dir = navIndex(toPath) < navIndex(fromPath) ? -1 : 1 // -1=back, 1=forward

  // ---- setup: position old + new panes ----
  isSliding.value = false

  nextPane.value = { key, component: comp }
  currentX.value = 0

  if (dir === 1) {
    // Forward: new page enters from right
    nextX.value = 100
  } else {
    // Backward: new page enters from left
    nextX.value = -100
  }

  await nextTick()

  // Force browser to paint initial positions before animating
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))

  // ---- animate ----
  isSliding.value = true
  await nextTick()

  if (dir === 1) {
    currentX.value = -100
    nextX.value = 0
  } else {
    currentX.value = 100
    nextX.value = 0
  }

  // ---- cleanup ----
  setTimeout(() => {
    currentPane.value = { key, component: comp }
    nextPane.value = null
    currentX.value = 0
    nextX.value = dir === 1 ? 100 : -100
    isSliding.value = false
    lastPath = toPath
    locked = false
  }, DURATION + 80)
}

// ---- route watcher ----
watch(
  () => route.fullPath,
  (to, from) => {
    if (!from) {
      const c = resolveComponent(route)
      if (c) { currentPane.value = { key: to, component: c }; lastPath = to }
      return
    }
    if (to === from || to === lastPath) return
    animate(from, to)
  },
  { immediate: true }
)
</script>

<style>
/* ---- stage: fixed below TopNav, seamless background ---- */
.slide-stage {
  position: fixed;
  inset: 64px 0 0;
  overflow: hidden;
  background: #f1f7fb;
}

/* ---- pane: absolutely positioned, GPU-composited ---- */
.slide-pane {
  position: absolute;
  inset: 0;
  overflow-y: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
  will-change: transform;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
}

.slide-pane::-webkit-scrollbar {
  width: 0;
  height: 0;
  display: none;
}

.slide-pane.moving {
  transition: transform 0.55s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ---- transparent page backgrounds → stage background shows through ---- */
.slide-pane .home-cover,
.slide-pane .chat-page,
.slide-pane .resource-center-page,
.slide-pane .resource-page,
.slide-pane .study-panel,
.slide-pane .my-full-page,
.slide-pane .profile-page,
.slide-pane .question-bank-page,
.slide-pane .quiz-runner-page,
.slide-pane .import-page,
.slide-pane .presentation-player {
  background: transparent !important;
}

@media (max-width: 640px) {
  .slide-stage {
    inset: 56px 0 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .slide-pane.moving {
    transition: none;
  }
}
</style>
