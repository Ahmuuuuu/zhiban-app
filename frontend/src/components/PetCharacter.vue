<script setup lang="ts">
import petImage from "../assets/pic/zhiban-pet-base.png";

defineProps<{
  state: string;
  dragging?: boolean;
}>();
</script>

<template>
  <div
    class="pet-character__stage"
    :class="[`state--${state}`, { 'pet-character--dragging': dragging }]"
  >
    <img class="pet-character__image" :src="petImage" alt="" draggable="false" />
    <span class="pet-character__loading-ring" />
    <span class="pet-character__thought"><i /><i /><i /></span>
    <span class="pet-character__wave" />
    <span class="pet-character__page-flip" />
    <span class="pet-character__tear" />
    <span class="pet-character__sparkles"><i /><i /><i /></span>
  </div>
</template>

<style scoped>
.pet-character__stage {
  position: relative;
  width: 100%;
  height: 100%;
  animation: char-idle 3.6s ease-in-out infinite;
  transform-origin: 50% 88%;
}

.pet-character--dragging {
  animation-play-state: paused;
}

.state--waiting { animation: char-waiting 1.8s ease-in-out infinite; }
.state--thinking { animation: char-thinking 2.2s ease-in-out infinite; }
.state--greeting { animation: char-greeting 1.35s ease-in-out infinite; }
.state--loading { animation: char-loading-pulse 1.6s ease-in-out infinite; }
.state--studying { animation: char-studying 2.4s ease-in-out infinite; }
.state--failed { animation: char-failed 1.8s ease-in-out infinite; }
.state--success { animation: char-success 1.35s ease-in-out infinite; }

.pet-character__image {
  position: relative;
  z-index: 2;
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  pointer-events: none;
  -webkit-user-drag: none;
}

.pet-character__loading-ring,
.pet-character__thought,
.pet-character__wave,
.pet-character__page-flip,
.pet-character__tear,
.pet-character__sparkles {
  position: absolute;
  pointer-events: none;
  opacity: 0;
}

.pet-character__loading-ring {
  z-index: 1;
  inset: 8%;
  border-radius: 999px;
  background: conic-gradient(from 0deg, rgba(97, 225, 255, 0), rgba(97, 225, 255, 0.72), rgba(97, 225, 255, 0));
  mask: radial-gradient(circle, transparent 62%, #000 63%);
}

.state--loading .pet-character__loading-ring {
  opacity: 1;
  animation: char-ring 1s linear infinite;
}

.pet-character__thought {
  z-index: 3;
  left: 12%;
  top: 7%;
  width: 30%;
  height: 13%;
}

.pet-character__thought i {
  position: absolute;
  display: block;
  width: 22%;
  aspect-ratio: 1;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 4px 12px rgba(40, 136, 205, 0.2);
}

.pet-character__thought i:nth-child(1) { left: 0; bottom: 4%; }
.pet-character__thought i:nth-child(2) { left: 30%; top: 24%; }
.pet-character__thought i:nth-child(3) { right: 6%; top: 0; }

.state--thinking .pet-character__thought,
.state--waiting .pet-character__thought {
  opacity: 1;
  animation: char-pop 1.6s ease-in-out infinite;
}

.pet-character__wave {
  z-index: 3;
  right: 5%;
  top: 31%;
  width: 18%;
  height: 18%;
  border: 4px solid rgba(80, 211, 255, 0.8);
  border-left-color: transparent;
  border-bottom-color: transparent;
  border-radius: 50%;
  transform: rotate(-18deg);
}

.state--greeting .pet-character__wave {
  opacity: 1;
  animation: char-wave-mark 0.8s ease-in-out infinite;
}

.pet-character__page-flip {
  z-index: 4;
  left: 31%;
  top: 52%;
  width: 24%;
  height: 17%;
  border-radius: 58% 12% 22% 18%;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(210, 238, 255, 0.4));
  transform-origin: 92% 82%;
  transform: rotate(-10deg) scaleX(0);
}

.state--studying .pet-character__page-flip {
  opacity: 1;
  animation: char-page 1.3s ease-in-out infinite;
}

.pet-character__tear {
  z-index: 4;
  left: 33%;
  top: 43%;
  width: 5%;
  height: 8%;
  border-radius: 58% 58% 58% 12%;
  background: linear-gradient(180deg, #72eaff, #1593dd);
  transform: rotate(24deg);
}

.state--failed .pet-character__tear {
  opacity: 1;
  animation: char-tear 1.4s ease-in-out infinite;
}

.pet-character__sparkles {
  z-index: 4;
  inset: 3% 0 auto auto;
  width: 38%;
  height: 32%;
}

.pet-character__sparkles i {
  position: absolute;
  display: block;
  width: 14%;
  aspect-ratio: 1;
  background: #fff9a8;
  clip-path: polygon(50% 0, 62% 36%, 100% 50%, 62% 64%, 50% 100%, 38% 64%, 0 50%, 38% 36%);
  filter: drop-shadow(0 0 8px rgba(255, 241, 92, 0.72));
}

.pet-character__sparkles i:nth-child(1) { left: 10%; top: 35%; }
.pet-character__sparkles i:nth-child(2) { right: 12%; top: 8%; width: 18%; }
.pet-character__sparkles i:nth-child(3) { right: 24%; bottom: 12%; width: 11%; }

.state--success .pet-character__sparkles {
  opacity: 1;
  animation: char-pop 1s ease-in-out infinite;
}

@keyframes char-idle {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-6px) scale(1.01); }
}

@keyframes char-waiting {
  0%, 100% { transform: translateY(0) rotate(0); }
  32% { transform: translateY(-5px) rotate(-2.2deg); }
  66% { transform: translateY(-5px) rotate(2.2deg); }
}

@keyframes char-thinking {
  0%, 100% { transform: translateY(0) rotate(0); }
  50% { transform: translateY(-5px) rotate(-3deg); }
}

@keyframes char-greeting {
  0%, 100% { transform: translateY(0) rotate(-1deg); }
  35% { transform: translateY(-9px) rotate(4deg); }
  70% { transform: translateY(-4px) rotate(-3deg); }
}

@keyframes char-loading-pulse {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-4px) scale(0.985); }
}

@keyframes char-studying {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

@keyframes char-failed {
  0%, 100% { transform: translateY(7px) rotate(0) scale(0.985); }
  26% { transform: translateY(7px) rotate(-1.8deg) scale(0.985); }
  52% { transform: translateY(7px) rotate(1.8deg) scale(0.985); }
}

@keyframes char-success {
  0%, 100% { transform: translateY(0) scale(1); }
  40% { transform: translateY(-18px) scale(1.04); }
  72% { transform: translateY(2px) scale(0.99); }
}

@keyframes char-ring { to { transform: rotate(360deg); } }

@keyframes char-pop {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-5px) scale(1.08); }
}

@keyframes char-wave-mark {
  0%, 100% { transform: rotate(-18deg) scale(0.82); }
  50% { transform: rotate(-18deg) scale(1.1); }
}

@keyframes char-page {
  0% { transform: rotate(-12deg) scaleX(0); opacity: 0; }
  25% { opacity: 0.95; }
  60% { transform: rotate(12deg) scaleX(1); opacity: 0.75; }
  100% { transform: rotate(18deg) scaleX(0); opacity: 0; }
}

@keyframes char-tear {
  0%, 100% { transform: translateY(0) rotate(24deg) scale(0.8); }
  50% { transform: translateY(10px) rotate(24deg) scale(1); }
}

@media (prefers-reduced-motion: reduce) {
  .pet-character__stage,
  .pet-character__stage * {
    animation: none;
  }
}
</style>
