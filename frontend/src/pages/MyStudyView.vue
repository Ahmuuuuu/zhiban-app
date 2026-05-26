<template>
  <div class="my-full-page">
    <main class="main">
      <header class="topbar">
        <PageBackButton />
        <router-link class="home-pill" to="/" aria-label="&#x8FD4;&#x56DE;&#x9996;&#x9875;">
          &#x9996;&#x9875;
        </router-link>

        <div class="title-block">
          <p>Mine</p>
          <h1>閹存垹娈?/h1>
        </div>

        <label class="search-field">
          <Search :size="18" />
          <input type="search" placeholder="閹兼粎鍌ㄧ拠鍓р柤閵嗕浇顓搁崚鎺嬧偓渚€鏁婃０?.." />
        </label>

        <UserAccountButton variant="dark" meta-type="major" logged-out-name="閺堫亞娅ヨぐ? />
      </header>

      <section class="my-page">
        <aside class="my-side">
          <h2>鐎佃壈鍩?/h2>
          <nav class="my-tabs" aria-label="閹存垹娈戠€涳缚绡勭€佃壈鍩?>
            <button
              class="my-tab resource-trigger"
              type="button"
              :class="{ active: isResourcesPage }"
              @click="toggleResourcePicker"
            >
              <BookOpenText :size="18" />
              <span>鐎涳缚绡勭挧鍕爱</span>
            </button>

            <Transition name="resource-picker-slide">
              <div v-if="resourcePickerOpen" class="resource-picker">
                <div class="picker__group">
                  <span class="picker__label">鐠у嫭绨崚鍡欒</span>
                  <div class="picker__tags">
                    <button
                      v-for="item in resourceCategories"
                      :key="item.value"
                      type="button"
                      class="picker__tag"
                      :class="{ active: activeCategory === item.value }"
                      @click="setResourceCategory(item.value)"
                    >
                      {{ item.label }}
                    </button>
                  </div>
                </div>

                <Transition name="sub-picker-slide">
                  <div v-if="activeCategory === 'document'" class="picker__group">
                    <span class="picker__label">閺傚洦銆傜€涙劕鍨庣猾?/span>
                    <div class="picker__tags">
                      <button
                        v-for="item in subCategories"
                        :key="item.value"
                        type="button"
                        class="picker__tag"
                        :class="{ active: activeSubCategory === item.value }"
                        @click="setSubCategory(item.value)"
                      >
                        {{ item.label }}
                      </button>
                    </div>
                  </div>
                </Transition>
              </div>
            </Transition>

            <router-link class="my-tab" to="/mine/path" @click="resourcePickerOpen = false">
              <Route :size="18" />
              <span>鐎涳缚绡勭捄顖氱窞</span>
            </router-link>

            <router-link class="my-tab" to="/mine/situation" @click="resourcePickerOpen = false">
              <ChartNoAxesColumnIncreasing :size="18" />
              <span>鐎涳缚绡勯幆鍛枌</span>
            </router-link>
          </nav>
        </aside>

        <div class="my-content">
          <router-view v-slot="{ Component, route: childRoute }">
            <Transition name="my-content-swap" mode="out-in">
              <component :is="Component" :key="childRoute.name" />
            </Transition>
          </router-view>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BookOpenText, ChartNoAxesColumnIncreasing, Route, Search } from 'lucide-vue-next'
import UserAccountButton from '../components/UserAccountButton.vue'
import PageBackButton from '../components/PageBackButton.vue'

const route = useRoute()
const router = useRouter()
const resourcePickerOpen = ref(false)

const resourceCategories = [
  { value: 'document', label: '閺傚洦銆? },
  { value: 'ppt', label: 'PPT' },
  { value: 'video', label: '鐟欏棝顣? },
  { value: 'quiz', label: '妫版ê绨? },
  { value: 'mindmap', label: '閹繄娣€电厧娴? }
]

const subCategories = [
  { value: 'all', label: '閸忋劑鍎? },
  { value: 'knowledge_point', label: '閻儴鐦戦悙纭咁唹鐟? },
  { value: 'exercise', label: '娑旂娀顣?妫版ê绨? },
  { value: 'textbook', label: '閺佹瑧顫栨稊锔剧彿閼? },
  { value: 'note', label: '鐎涳缚绡勭粭鏃囶唶' },
  { value: 'case_study', label: '鐎圭偞鎼峰鍫滅伐' },
  { value: 'reference', label: '閸欏倽鈧啳绁弬? }
]

const isResourcesPage = computed(() => route.path === '/mine/resources')
const activeCategory = computed(() => String(route.query.category || 'document'))
const activeSubCategory = computed(() => String(route.query.sub || 'all'))

const goResources = query => {
  router.push({
    path: '/mine/resources',
    query: {
      category: activeCategory.value,
      ...(activeCategory.value === 'document' ? { sub: activeSubCategory.value } : {}),
      ...query
    }
  })
}

const toggleResourcePicker = () => {
  resourcePickerOpen.value = !resourcePickerOpen.value

  if (!isResourcesPage.value) {
    goResources({})
  }
}

const setResourceCategory = category => {
  goResources({
    category,
    ...(category === 'document' ? { sub: activeSubCategory.value } : { sub: undefined })
  })
}

const setSubCategory = sub => {
  goResources({ category: 'document', sub })
}

watch(() => route.path, path => {
  if (path !== '/mine/resources') {
    resourcePickerOpen.value = false
  }
})
</script>

<style scoped>
* {
  box-sizing: border-box;
}

.my-full-page {
  width: 100vw;
  height: 100vh;
  background:
    radial-gradient(ellipse 72% 44% at 10% 0%, rgba(209, 244, 250, 0.46), transparent 70%),
    linear-gradient(135deg, #fafafa 0%, rgb(237, 249, 252) 52%, #fafafa 100%);
  color: #163f8f;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
  display: grid;
  overflow: hidden;
}

.main {
  min-width: 0;
  height: 100vh;
  padding: 28px 34px;
  overflow: hidden;
}

.topbar {
  display: grid;
  grid-template-columns: 62px 150px minmax(280px, 1fr) auto;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
}

.home-pill,
.search-field,
.my-side,
.my-content,
.resource-picker {
  border: 1px solid rgba(22, 63, 143, 0.16);
  background: rgba(250, 250, 250, 0.78);
  color: #163f8f;
  box-shadow:
    0 14px 34px rgba(22, 63, 143, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(14px) saturate(135%);
  -webkit-backdrop-filter: blur(14px) saturate(135%);
}

.home-pill {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 800;
}

.title-block p {
  margin: 0 0 5px;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 800;
}

.title-block h1 {
  margin: 0;
  color: #163f8f;
  font-size: 28px;
  font-weight: 900;
  line-height: 1.15;
}

.search-field {
  width: 100%;
  height: 42px;
  padding: 0 14px;
  border: 2px solid rgba(22, 63, 143, 0.86);
  border-radius: 18px;
  background: rgba(250, 250, 250, 0.88);
  box-shadow: none;
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-field input {
  width: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: #163f8f;
  font: inherit;
}

.search-field input::placeholder {
  color: rgba(22, 63, 143, 0.58);
}

.topbar :deep(.account-entry.dark) {
  min-width: 128px;
  max-width: 156px;
  height: 46px;
  min-height: 46px;
  padding: 0 14px 0 7px;
  border-radius: 24px;
}

.topbar :deep(.account-entry.dark .account-avatar) {
  width: 32px;
  height: 32px;
  font-size: 13px;
}

.topbar :deep(.account-entry.dark .account-text strong),
.topbar :deep(.account-entry.dark .account-text small) {
  max-width: 86px;
}

.my-page {
  height: calc(100vh - 110px);
  min-height: 0;
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);
  gap: 24px;
  overflow: hidden;
}

.my-side,
.my-content {
  min-height: 0;
  border-radius: 28px;
}

.my-side {
  position: relative;
  z-index: 5;
  overflow: visible;
  display: flex;
  flex-direction: column;
}

.my-side h2 {
  position: relative;
  margin: 0;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #163f8f;
  font-size: 21px;
}

.my-tabs {
  position: relative;
  display: grid;
  gap: 7px;
}

.my-tab {
  position: relative;
  width: calc(100% - 28px);
  height: 42px;
  margin: 0 14px;
  border: 0;
  border-radius: 999px;
  background: rgba(250, 250, 250, 0.48);
  color: #163f8f;
  text-decoration: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font: inherit;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.2s ease;
}

.my-side h2::after,
.my-tab::after {
  content: "";
  position: absolute;
  left: 24px;
  right: 24px;
  bottom: 0;
  height: 2px;
  border-radius: 999px;
  background:
    linear-gradient(to right, transparent 0%, rgba(201, 220, 233, 0.34) 24%, rgba(201, 220, 233, 0.72) 48%, rgba(201, 220, 233, 0.72) 52%, rgba(201, 220, 233, 0.34) 76%, transparent 100%),
    linear-gradient(to right, transparent 0%, transparent 42%, rgba(201, 220, 233, 0.9) 42%, rgba(201, 220, 233, 0.9) 58%, transparent 58%, transparent 100%);
  opacity: 0.66;
}

.my-tab:hover,
.my-tab.router-link-active,
.my-tab.active {
  background: rgba(201, 220, 233, 0.72);
  transform: translateY(-1px);
}

.resource-picker {
  position: absolute;
  left: calc(100% + 14px);
  top: 0;
  z-index: 20;
  width: 280px;
  padding: 16px;
  border-radius: 22px;
  display: grid;
  gap: 14px;
}

.picker__group {
  display: grid;
  gap: 10px;
}

.picker__label {
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
}

.picker__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.picker__tag {
  min-height: 36px;
  padding: 0 16px;
  border: 1px solid rgba(22, 63, 143, 0.14);
  border-radius: 18px;
  background: rgba(250, 250, 250, 0.68);
  color: #163f8f;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 14px 34px rgba(22, 63, 143, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.64);
  backdrop-filter: blur(14px) saturate(135%);
  -webkit-backdrop-filter: blur(14px) saturate(135%);
}

.picker__tag:hover {
  background: rgba(201, 220, 233, 0.72);
  border-color: #5f8fc3;
}

.picker__tag.active {
  background: rgba(201, 220, 233, 0.72);
  color: #163f8f;
  border-color: #5f8fc3;
  box-shadow: 0 0 0 2px rgba(95, 143, 195, 0.24), 0 14px 34px rgba(22, 63, 143, 0.08);
}

.sub-picker-slide-enter-active,
.sub-picker-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.22s cubic-bezier(0.22, 1, 0.36, 1);
}

.sub-picker-slide-enter-from,
.sub-picker-slide-leave-to {
  opacity: 0;
  transform: translateX(-10px) scale(0.98);
}

.resource-picker-slide-enter-active,
.resource-picker-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.22s cubic-bezier(0.22, 1, 0.36, 1);
}

.resource-picker-slide-enter-from,
.resource-picker-slide-leave-to {
  opacity: 0;
  transform: translateX(-10px) scale(0.98);
}

.my-content {
  overflow: hidden;
}

.my-content-swap-enter-active,
.my-content-swap-leave-active {
  transition: opacity 0.12s ease;
}

.my-content-swap-enter-from,
.my-content-swap-leave-to {
  opacity: 0;
}

@media (max-width: 980px) {
  .my-full-page,
  .main {
    height: auto;
    min-height: 100vh;
    overflow: visible;
  }

  .topbar,
  .my-page {
    grid-template-columns: 1fr;
  }

  .my-page {
    height: auto;
    overflow: visible;
  }

  .resource-picker {
    position: static;
    width: calc(100% - 28px);
    margin: 0 14px;
  }

  .my-content {
    overflow: visible;
  }
}
</style>
