<template>
  <main class="home-cover">
    <section class="hero" aria-label="知伴首页">
      <div class="hero-background" aria-hidden="true">
        <span class="sweep sweep-one"></span>
        <span class="sweep sweep-two"></span>
      </div>

      <div class="center-title">
        <p class="eyebrow">Personal Learning Companion</p>
        <h1>
          <span>AI学习助手</span>
          <span>知伴</span>
        </h1>
        <span class="sun-mark" aria-hidden="true"></span>
        <div class="hero-actions">
          <router-link class="primary-action" to="/chat">开始 AI 对话</router-link>
        </div>
      </div>

      <router-link
        v-for="tile in featureTiles"
        :key="tile.title"
        class="feature-tile"
        :class="tile.className"
        :to="tile.to"
        :aria-label="tile.title"
      >
        <img :src="tile.image" :alt="tile.title" />
        <span v-if="tile.title" class="tile-copy">
          <strong>{{ tile.title }}</strong>
          <small v-if="tile.subtitle">{{ tile.subtitle }}</small>
        </span>
      </router-link>

      <div class="quick-panel">
        <router-link to="/resources">
          <strong>资源中心</strong>
          <span>讲义、题库、课件统一管理</span>
        </router-link>
        <router-link to="/learning-resources">
          <strong>我的资源</strong>
          <span>收藏与生成内容随时回看</span>
        </router-link>
        <router-link to="/learning-situation">
          <strong>学习情况</strong>
          <span>进度、薄弱点、活跃趋势</span>
        </router-link>
      </div>
    </section>
  </main>
</template>

<script setup>
import resourceImage from '../assets/pic/a5e56fcc-c654-437a-a2cb-a71a7a5ec871.png'
import originalPathImage from '../assets/pic/8fa2bb78-91c9-4ac9-991a-00c9c43408dd.png'
import studyPathImage from '../assets/pic/学习路径.png'
import createResourceImage from '../assets/pic/资源生成.png'
import situationImage from '../assets/pic/屏幕截图 2026-05-30 182715.png'
import petImage from '../assets/pic/24d45e90-dddc-4df5-bb2b-e866c3ed6344.png'
const featureTiles = [
  {
    title: '资源生成',
    subtitle: '',
    to: '/study-import',
    image: resourceImage,
    className: 'tile-chat',
  },
  {
    title: '资源中心',
    subtitle: '',
    to: '/resources',
    image: createResourceImage,
    className: 'tile-resource',
  },
  {
    title: '用户画像',
    subtitle: '',
    to: '/profile',
    image: originalPathImage,
    className: 'tile-path',
  },
  {
    title: '解答问题',
    subtitle: '',
    to: '/learning-situation',
    image: situationImage,
    className: 'tile-situation',
  },
  {
    title: '小知陪学',
    subtitle: '随时唤起学习伙伴',
    to: '/chat',
    image: petImage,
    className: 'tile-pet',
  },
  {
    title: '',
    subtitle: '',
    to: '/profile',
    image: studyPathImage,
    className: 'tile-profile',
  },
]
</script>

<style scoped>
@font-face {
  font-family: "Smiley Sans";
  src: url("../assets/fonts/SmileySans-Oblique.woff2") format("woff2");
  font-weight: 400 900;
  font-style: oblique;
  font-display: swap;
}

.home-cover {
  min-height: 100vh;
  color: #143761;
  font-family:
    Inter,
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    "PingFang SC",
    "Microsoft YaHei",
    sans-serif;
  overflow: hidden;
}

.hero {
  position: relative;
  min-height: calc(100vh - 64px);
  padding: 28px clamp(18px, 4vw, 70px) 34px;
  display: grid;
  place-items: center;
  isolation: isolate;
}

.hero-background {
  position: absolute;
  inset: 0;
  z-index: -2;
  background: #f1f7fb;
  overflow: hidden;
}

.hero-background::before,
.hero-background::after {
  content: "";
  position: absolute;
  background: #e9eff3;
  border-radius: 50%;
}

.hero-background::before {
  width: clamp(540px, 62vw, 760px);
  height: clamp(540px, 62vw, 760px);
  left: 50%;
  top: -96px;
  transform: translateX(-50%);
}

.hero-background::after {
  width: clamp(420px, 48vw, 620px);
  height: clamp(420px, 48vw, 620px);
  right: clamp(-280px, -18vw, -170px);
  bottom: clamp(-310px, -24vw, -210px);
}

.sweep {
  position: absolute;
  display: block;
  width: clamp(320px, 34vw, 520px);
  height: clamp(320px, 34vw, 520px);
  border-radius: 50%;
  background: #e9eff3;
}

.sweep-one {
  left: clamp(-250px, -14vw, -140px);
  top: 118px;
}

.sweep-two {
  right: clamp(-220px, -12vw, -130px);
  top: -92px;
}

.sun-mark {
  position: relative;
  display: block;
  width: clamp(34px, 3.9vw, 48px);
  height: clamp(34px, 3.9vw, 48px);
  margin: 22px auto 0;
  background:
    linear-gradient(#f0a73a, #f0a73a) center / 100% 2px no-repeat,
    linear-gradient(#f0a73a, #f0a73a) center / 2px 100% no-repeat;
}

.sun-mark::before,
.sun-mark::after {
  content: "";
  position: absolute;
  left: 50%;
  top: 50%;
  width: 100%;
  height: 2px;
  background: #f0a73a;
  transform-origin: center;
}

.sun-mark::before {
  transform: translate(-50%, -50%) rotate(45deg);
}

.sun-mark::after {
  transform: translate(-50%, -50%) rotate(-45deg);
}

.center-title {
  position: relative;
  z-index: 3;
  width: min(900px, 88vw);
  margin-top: -38px;
  text-align: center;
}

.eyebrow {
  margin: -10px 0 40px;
  color: #6da3d2;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0;
}

.center-title h1 {
  margin: 0;
  color: #143761;
  font-family:
    "Smiley Sans",
    "PingFang SC",
    "Microsoft YaHei",
    sans-serif;
  font-size: clamp(64px, 9.8vw, 148px);
  line-height: 0.9;
  letter-spacing: 0;
  font-weight: 900;
  -webkit-text-stroke: 1.2px #143761;
  text-shadow:
    0.8px 0 #143761,
    -0.8px 0 #143761,
    0 0.8px #143761,
    0 -0.8px #143761;
}

.center-title h1 span {
  display: block;
  transform: scaleY(0.88);
  transform-origin: center;
}

.center-title h1 span:first-child {
  margin-bottom: clamp(10px, 1.2vw, 18px);
  white-space: nowrap;
}

.hero-actions {
  margin-top: 28px;
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 12px;
}

.primary-action {
  height: 44px;
  padding: 0 22px;
  border-radius: 999px;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 800;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.primary-action {
  background: #143761;
  color: #ffffff;
  box-shadow: 0 12px 24px rgba(20, 55, 97, 0.18);
}

.primary-action:hover,
.feature-tile:hover,
.quick-panel a:hover {
  transform: translateY(-3px);
}

.feature-tile {
  position: absolute;
  z-index: 1;
  overflow: hidden;
  text-decoration: none;
  color: #143761;
  background: #dcebf2;
  box-shadow: 0 18px 38px rgba(31, 68, 103, 0.13);
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}

.feature-tile:hover {
  box-shadow: 0 24px 44px rgba(31, 68, 103, 0.18);
}

.feature-tile img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.tile-copy {
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 12px;
  min-height: 52px;
  padding: 9px 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  display: grid;
  align-content: center;
  gap: 3px;
}

.tile-copy strong {
  font-size: 15px;
  line-height: 1.2;
}

.tile-copy small {
  color: #5d7d97;
  font-size: 12px;
  line-height: 1.35;
}

.tile-chat {
  left: clamp(18px, 5vw, 74px);
  top: 7vh;
  width: clamp(118px, 13vw, 176px);
  aspect-ratio: 1;
  border-radius: 50%;
}

.tile-chat .tile-copy {
  display: none;
}

.tile-resource {
  left: clamp(86px, 13vw, 214px);
  top: 34vh;
  width: clamp(150px, 17vw, 240px);
  aspect-ratio: 1.28;
  border-radius: 42px 0 42px 0;
}

.tile-resource img {
  object-position: center;
}

.tile-resource .tile-copy {
  display: none;
}

.tile-path {
  left: clamp(22px, 7vw, 130px);
  top: 60vh;
  bottom: auto;
  width: clamp(140px, 17vw, 232px);
  aspect-ratio: 1.45;
  border-radius: 46px 46px 0 0;
}

.tile-path .tile-copy {
  display: none;
}

.tile-situation {
  right: 19vw;
  top: 32vh;
  width: clamp(138px, 16vw, 220px);
  aspect-ratio: 1.08;
  border-radius: 54px 0 0 0;
}

.tile-situation .tile-copy {
  display: none;
}

.tile-pet {
  right: clamp(18px, 5vw, 78px);
  top: 7vh;
  width: clamp(124px, 13vw, 182px);
  aspect-ratio: 1;
  border-radius: 50%;
  background: #ffffff;
}

.tile-pet img {
  object-fit: cover;
  padding: 0;
  box-sizing: border-box;
}

.tile-pet .tile-copy {
  display: none;
}

.tile-profile {
  right: clamp(18px, 9vw, 130px);
  top: 64vh;
  bottom: auto;
  width: clamp(150px, 17vw, 236px);
  aspect-ratio: 1.28;
  border-radius: 0 42px 0 42px;
}

.tile-profile .tile-copy {
  display: none;
}

.quick-panel {
  position: absolute;
  z-index: 2;
  right: clamp(18px, 4vw, 62px);
  bottom: 32px;
  display: none;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.quick-panel a {
  min-width: 0;
  padding: 14px 16px;
  border-radius: 8px;
  border: 1px solid rgba(181, 205, 220, 0.8);
  background: rgba(255, 255, 255, 0.72);
  color: #143761;
  text-decoration: none;
  display: grid;
  gap: 5px;
  transition: transform 0.2s ease, background 0.2s ease;
}

.quick-panel strong {
  font-size: 14px;
}

.quick-panel span {
  color: #5d7d97;
  font-size: 12px;
  line-height: 1.45;
}

@media (min-width: 1180px) and (max-height: 780px) {
  .quick-panel {
    display: grid;
    width: min(520px, 45vw);
  }

  .tile-profile {
    display: none;
  }
}

@media (max-width: 980px) {
  .hero {
    min-height: auto;
    padding: 54px 22px 36px;
    align-content: start;
    gap: 18px;
  }

  .hero-background::before {
    width: 86vw;
    height: 86vw;
    min-width: 0;
    min-height: 0;
    top: -8vw;
  }

  .center-title {
    width: 100%;
    margin: 0 0 12px;
  }

  .feature-tile {
    position: relative;
    left: auto;
    right: auto;
    top: auto;
    bottom: auto;
    width: min(100%, 420px);
    border-radius: 18px;
    aspect-ratio: 1.75;
    justify-self: center;
  }

  .feature-tile img {
    object-fit: cover;
  }

  .tile-pet img {
    padding: 10px 10px 56px;
  }

  .quick-panel {
    position: relative;
    right: auto;
    bottom: auto;
    display: grid;
    width: min(100%, 420px);
    grid-template-columns: 1fr;
    margin-top: 4px;
  }
}

@media (max-width: 640px) {
  .hero {
    padding: 34px 16px 28px;
  }

  .center-title h1 {
    font-size: clamp(48px, 17vw, 76px);
  }

  .lead {
    font-size: 15px;
  }

  .hero-actions {
    justify-content: stretch;
  }

  .primary-action,
  .secondary-action {
    width: 100%;
  }

  .tile-chat,
  .tile-pet {
    aspect-ratio: 1.55;
  }

  .sun-mark {
    top: 30%;
  }
}
</style>
