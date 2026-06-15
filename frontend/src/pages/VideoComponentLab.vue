<template>
  <main class="video-lab">
    <header class="lab-header">
      <div>
        <span>Video Component Lab</span>
        <h1>视频组件预览台</h1>
      </div>
      <p>这里专门用来逐个看视频组件效果，改组件样式后刷新这一页就能对比。</p>
    </header>

    <section class="lab-section lab-section--wide">
      <div class="section-title">
        <span>完整组件</span>
        <h2>VideoPreview</h2>
      </div>
      <div class="preview-frame preview-frame--full">
        <VideoPreview
          title="六级英语作文结构讲解"
          :content="sampleContent"
          fallback-text="这里展示没有真实视频文件时的空状态。"
        />
      </div>
    </section>

    <section class="lab-grid">
      <article class="lab-section">
        <div class="section-title">
          <span>舞台背景</span>
          <h2>VideoAmbientBackground</h2>
        </div>
        <div class="stage-demo">
          <VideoAmbientBackground :background-url="backgroundUrl" active />
          <VideoStageInfo :chapter-count="6" duration-label="03:20" />
          <VideoWaveform active />
        </div>
      </article>

      <article class="lab-section">
        <div class="section-title">
          <span>视频封面</span>
          <h2>VideoPoster</h2>
        </div>
        <div class="poster-demo">
          <VideoPoster
            :poster-url="backgroundUrl"
            title="核心词汇与场景识别"
            summary="用机场、酒店、医疗三个场景串起听力关键词，帮助快速判断题目语境。"
          />
        </div>
      </article>

      <article class="lab-section">
        <div class="section-title">
          <span>播放状态</span>
          <h2>Status / Progress</h2>
        </div>
        <div class="stack-demo">
          <VideoStatusBadge has-source />
          <VideoStatusBadge has-source has-started />
          <VideoStatusBadge has-source has-started is-playing />
          <VideoGlowProgress :current-time="78" :duration="180" />
        </div>
      </article>

      <article class="lab-section">
        <div class="section-title">
          <span>导航与讲稿</span>
          <h2>Chapter / Transcript</h2>
        </div>
        <div class="stack-demo">
          <VideoChapterList
            :chapters="chapters"
            active-chapter-id="chapter-1"
          />
          <VideoTranscriptPanel :paragraphs="transcript" />
        </div>
      </article>
    </section>

    <section class="lab-section lab-section--wide">
      <div class="section-title">
        <span>幻灯片画面</span>
        <h2>VideoSlideCanvas</h2>
      </div>
      <div class="slide-grid">
        <article
          v-for="item in slides"
          :key="item.name"
          class="slide-demo"
        >
          <header>
            <span>{{ item.name }}</span>
            <b>{{ item.note }}</b>
          </header>
          <div class="slide-stage">
            <VideoAmbientBackground :background-url="backgroundUrl" active />
            <VideoSlideCanvas
              :slide="item.slide"
              :slide-count="slides.length"
              duration-label="02:45"
              is-playing
              has-started
            >
              <template #progress>
                <div class="slide-progress">
                  <VideoGlowProgress :current-time="item.progress" :duration="165" />
                </div>
              </template>
            </VideoSlideCanvas>
          </div>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup>
import VideoAmbientBackground from '../components/ppt_video/video/VideoAmbientBackground.vue'
import VideoChapterList from '../components/ppt_video/video/VideoChapterList.vue'
import VideoGlowProgress from '../components/ppt_video/video/VideoGlowProgress.vue'
import VideoPoster from '../components/ppt_video/video/VideoPoster.vue'
import VideoPreview from '../components/ppt_video/video/VideoPreview.vue'
import VideoStageInfo from '../components/ppt_video/video/VideoStageInfo.vue'
import VideoStatusBadge from '../components/ppt_video/video/VideoStatusBadge.vue'
import VideoTranscriptPanel from '../components/ppt_video/video/VideoTranscriptPanel.vue'
import VideoWaveform from '../components/ppt_video/video/VideoWaveform.vue'
import VideoSlideCanvas from '../components/ppt_video/video/slides/VideoSlideCanvas.vue'
import { selectVideoBackground } from '../components/ppt_video/video/videoAssets'

const sampleContent = [
  '# 六级英语作文结构讲解',
  '第一段用一句明确立场打开论点，避免绕弯铺垫。',
  '第二段展开两个核心理由，每个理由用例子支撑。',
  '结尾段总结观点，并给出可执行建议。',
].join('\n\n')

const backgroundUrl = selectVideoBackground({
  title: '六级英语作文结构讲解',
  content: sampleContent
})

const chapters = [
  { id: 'chapter-0', index: 0, title: '开篇立场定位' },
  { id: 'chapter-1', index: 1, title: '主体段理由展开' },
  { id: 'chapter-2', index: 2, title: '结尾升华写法' },
]

const transcript = [
  '先判断题目要求，再确定观点句。观点句越早出现，阅卷时越容易抓住文章方向。',
  '主体段不要堆概念，每个理由后面接一个具体例子，文章会更稳。',
  '结尾段可以用建议或展望收束，但不要引入新的复杂论点。',
]

const slides = [
  {
    name: 'KeyPointSlide',
    note: '适合知识点讲解',
    progress: 42,
    slide: {
      title: '三段式黄金结构',
      text: '引言段：明确立场\n主体段：理由 + 例子\n结尾段：总结 + 升华',
      notes: '强调每段的功能定位。',
      visual_hint: 'writing structure diagram'
    }
  },
  {
    name: 'VocabularySlide',
    note: '适合词汇和短语',
    progress: 86,
    slide: {
      title: '高频表达替换',
      text: 'important -> significant\nmany -> numerous\nhelp -> contribute to\nsolve -> address',
      notes: '展示替换前后的表达层次。',
      visual_hint: 'English vocabulary cards'
    }
  },
  {
    name: 'FormulaSlide',
    note: '适合公式和符号',
    progress: 128,
    slide: {
      title: '函数增长模型',
      text: '线性增长：y = kx + b\n指数增长：y = a^x\n对数增长：y = log_a x',
      notes: '注意公式需要清楚分行，不要挤在一段里。',
      visual_hint: 'math formula chart'
    }
  }
]
</script>

<style scoped>
.video-lab {
  min-height: 100vh;
  padding: 34px;
  background: #eef5f8;
  color: #163f8f;
}

.lab-header {
  max-width: 1180px;
  margin: 0 auto 24px;
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
}

.lab-header span,
.section-title span,
.slide-demo header span {
  color: #5f8fc3;
  font-size: 12px;
  font-weight: 900;
}

.lab-header h1,
.section-title h2 {
  margin: 4px 0 0;
  color: #163f8f;
  line-height: 1.15;
}

.lab-header h1 {
  font-size: 34px;
}

.lab-header p {
  max-width: 520px;
  margin: 0;
  color: rgba(31, 51, 86, 0.66);
  line-height: 1.7;
}

.lab-grid,
.slide-grid {
  max-width: 1180px;
  margin: 0 auto;
  display: grid;
  gap: 18px;
}

.lab-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.lab-section {
  min-width: 0;
  padding: 18px;
  border: 1px solid rgba(201, 220, 233, 0.86);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.76);
  box-shadow: 0 14px 34px rgba(22, 63, 143, 0.08);
}

.lab-section--wide {
  max-width: 1180px;
  margin: 0 auto 18px;
}

.section-title {
  margin-bottom: 14px;
}

.section-title h2 {
  font-size: 22px;
}

.preview-frame {
  min-height: 480px;
}

.preview-frame--full {
  height: 560px;
}

.stage-demo,
.poster-demo,
.slide-stage {
  position: relative;
  min-height: 310px;
  border-radius: 8px;
  overflow: hidden;
  background: #10213d;
}

.poster-demo {
  min-height: 310px;
}

.stack-demo {
  min-height: 310px;
  padding: 16px;
  border-radius: 8px;
  background: rgba(238, 245, 248, 0.86);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.slide-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.slide-demo {
  min-width: 0;
}

.slide-demo header {
  min-height: 44px;
  margin-bottom: 10px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.slide-demo header b {
  color: rgba(31, 51, 86, 0.68);
  font-size: 13px;
}

.slide-stage {
  aspect-ratio: 16 / 9;
  min-height: 0;
}

.slide-progress {
  position: absolute;
  z-index: 6;
  left: 18px;
  right: 18px;
  bottom: 16px;
}

@media (max-width: 980px) {
  .video-lab {
    padding: 18px;
  }

  .lab-header {
    display: block;
  }

  .lab-header p {
    margin-top: 10px;
  }

  .lab-grid,
  .slide-grid {
    grid-template-columns: 1fr;
  }

  .preview-frame--full {
    height: auto;
    min-height: 620px;
  }
}
</style>
