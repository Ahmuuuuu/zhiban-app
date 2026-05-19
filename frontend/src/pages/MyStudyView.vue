<template>
  <div class="my-full-page">
    <main class="main">
      <header class="topbar">
        <div class="topbar-left">
          <router-link class="home-btn" to="/" aria-label="返回首页">
            <ArrowLeft :size="18" />
            <span>返回首页</span>
          </router-link>

          <div class="search-box">
            <span>搜索课程、计划、错题...</span>
          </div>
        </div>

        <div class="user-box">
          <div class="avatar"></div>
          <div>
            <strong>我的学习</strong>
            <p>资源、情况与路径</p>
          </div>
        </div>
      </header>

      <section class="my-page">
        <aside class="my-side">
          <div class="my-side-head">
            <p>Mine</p>
            <h1>我的</h1>
          </div>

          <nav class="my-tabs" aria-label="我的学习导航">
            <router-link
              v-for="item in tabs"
              :key="item.to"
              class="my-tab"
              :to="item.to"
            >
              <component :is="item.icon" :size="18" />
              <span>{{ item.label }}</span>
            </router-link>
          </nav>
        </aside>

        <div class="my-content">
          <router-view />
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ArrowLeft, BookOpenText, ChartNoAxesColumnIncreasing, Route } from 'lucide-vue-next'

const tabs = [
  { label: '学习资源', to: '/mine/resources', icon: BookOpenText },
  { label: '学习情况', to: '/mine/situation', icon: ChartNoAxesColumnIncreasing },
  { label: '学习路径', to: '/mine/path', icon: Route }
]
</script>

<style scoped>
* {
  box-sizing: border-box;
}

.my-full-page {
  width: 100vw;
  height: 100vh;
  background: #fdfcf7;
  color: #163f8f;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
  display: grid;
  overflow: hidden;
}

.main {
  min-width: 0;
  height: 100vh;
  padding: 26px 30px 30px;
  overflow: hidden;
}

.topbar {
  height: 64px;
  display: grid;
  grid-template-columns: 1fr 210px;
  gap: 22px;
  align-items: center;
  margin-bottom: 24px;
}

.topbar-left {
  min-width: 0;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}

.home-btn {
  height: 42px;
  padding: 0 13px;
  border: 1px solid #c9dce9;
  border-radius: 28px;
  background: #fafafa;
  color: #163f8f;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 14px;
  font-weight: 800;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    background 0.2s ease,
    border-color 0.2s ease;
}

.home-btn:hover {
  background: #c9dce9;
  border-color: #5f8fc3;
  box-shadow: 0 8px 18px rgba(22, 63, 143, 0.12);
  transform: translateY(-1px);
}

.search-box {
  height: 52px;
  padding: 0 22px;
  border: 1px solid rgba(201, 220, 233, 0.5);
  border-radius: 999px;
  background: rgba(250, 250, 250, 0.42);
  color: #5f8fc3;
  display: flex;
  align-items: center;
  backdrop-filter: blur(24px) saturate(155%);
  -webkit-backdrop-filter: blur(24px) saturate(155%);
  box-shadow:
    0 20px 46px rgba(22, 63, 143, 0.1),
    inset 0 1px 0 rgba(250, 250, 250, 0.64);
}

.user-box {
  height: 52px;
  padding: 7px 14px;
  border-radius: 14px;
  border: 1px solid #c9dce9;
  background: rgba(250, 250, 250, 0.48);
  backdrop-filter: blur(14px) saturate(135%);
  -webkit-backdrop-filter: blur(14px) saturate(135%);
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: linear-gradient(135deg, #d9c7b8, #f3e7dd);
  flex-shrink: 0;
}

.user-box strong {
  display: block;
  color: #163f8f;
  font-size: 14px;
}

.user-box p {
  margin: 2px 0 0;
  color: #5f8fc3;
  font-size: 12px;
}

.my-page {
  height: calc(100vh - 118px);
  min-height: 0;
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);
  gap: 18px;
  color: #163f8f;
  overflow: hidden;
}

.my-side,
.my-content {
  min-height: 0;
  border: 1px solid #c9dce9;
  border-radius: 28px;
  background: rgba(250, 250, 250, 0.68);
  backdrop-filter: blur(18px) saturate(135%);
  -webkit-backdrop-filter: blur(18px) saturate(135%);
}

.my-side {
  padding: 18px;
  background: #edf5fa;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.my-side-head p {
  margin: 0 0 6px;
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 800;
}

.my-side-head h1 {
  margin: 0;
  color: #163f8f;
  font-size: 28px;
  line-height: 1.15;
}

.my-tabs {
  display: grid;
  gap: 10px;
}

.my-tab {
  min-height: 42px;
  padding: 0 12px;
  border: 1px solid #c9dce9;
  border-radius: 18px;
  background: #fafafa;
  color: #163f8f;
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 14px;
  font-weight: 800;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    background 0.2s ease,
    border-color 0.2s ease;
}

.my-tab:hover,
.my-tab.router-link-active {
  background: #dcebf4;
  border-color: #5f8fc3;
  box-shadow: 0 8px 18px rgba(22, 63, 143, 0.12);
  transform: translateX(3px);
}

.my-content {
  overflow: hidden;
}

@media (max-width: 920px) {
  .my-full-page {
    height: auto;
    min-height: 100vh;
    overflow: visible;
  }

  .main {
    height: auto;
    min-height: 100vh;
    overflow: visible;
  }

  .topbar {
    grid-template-columns: 1fr;
    height: auto;
  }

  .topbar-left {
    grid-template-columns: 1fr;
  }

  .my-page {
    height: auto;
    min-height: calc(100vh - 118px);
    grid-template-columns: 1fr;
    overflow: visible;
  }

  .my-tabs {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .my-content {
    overflow: visible;
  }
}

@media (max-width: 640px) {
  .main {
    padding: 20px;
  }

  .my-tabs {
    grid-template-columns: 1fr;
  }
}
</style>
