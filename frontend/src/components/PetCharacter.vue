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
    <span class="pet-character__aura" />
    <span class="pet-character__ground" />
    <img class="pet-character__image" :src="petImage" alt="" draggable="false" />
    <span class="pet-character__loading-ring" />
    <span class="pet-character__thought"><i /><i /><i /></span>
    <span class="pet-character__wave" />
    <span class="pet-character__page-flip" />
    <span class="pet-character__tear" />
    <span class="pet-character__motifs"><i /><i /><i /><i /></span>
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
  will-change: transform;
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
  filter: drop-shadow(0 10px 10px rgba(24, 117, 184, 0.12));
  transform-origin: 50% 88%;
  animation: char-image-breathe 3.6s ease-in-out infinite;
}

.pet-character__aura,
.pet-character__ground,
.pet-character__loading-ring,
.pet-character__thought,
.pet-character__wave,
.pet-character__page-flip,
.pet-character__tear,
.pet-character__motifs,
.pet-character__sparkles {
  position: absolute;
  pointer-events: none;
}

.pet-character__aura {
  z-index: 0;
  inset: 14% 12% 5%;
  border-radius: 46% 52% 45% 55%;
  background:
    radial-gradient(circle at 42% 28%, rgba(255, 255, 255, 0.58), transparent 26%),
    radial-gradient(circle at 52% 58%, rgba(97, 225, 255, 0.22), transparent 58%);
  opacity: 0.65;
  filter: blur(3px);
  animation: char-aura 4.2s ease-in-out infinite;
}

.pet-character__ground {
  z-index: 0;
  left: 19%;
  right: 17%;
  bottom: 3%;
  height: 12%;
  border-radius: 50%;
  background: radial-gradient(ellipse, rgba(18, 90, 148, 0.22), rgba(18, 90, 148, 0) 68%);
  transform-origin: 50% 50%;
  animation: char-ground 3.6s ease-in-out infinite;
}

.pet-character__loading-ring,
.pet-character__thought,
.pet-character__wave,
.pet-character__page-flip,
.pet-character__tear,
.pet-character__motifs,
.pet-character__sparkles {
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
  animation: char-ring 1s linear infinite, char-ring-pulse 1.6s ease-in-out infinite;
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
}

.state--thinking .pet-character__thought i,
.state--waiting .pet-character__thought i {
  animation: char-bubble 1.8s ease-in-out infinite;
}

.state--thinking .pet-character__thought i:nth-child(2),
.state--waiting .pet-character__thought i:nth-child(2) {
  animation-delay: 160ms;
}

.state--thinking .pet-character__thought i:nth-child(3),
.state--waiting .pet-character__thought i:nth-child(3) {
  animation-delay: 320ms;
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

.pet-character__motifs {
  z-index: 1;
  inset: 8% 6% 12%;
}

.pet-character__motifs i {
  position: absolute;
  display: block;
  width: 7%;
  aspect-ratio: 1;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 0 12px rgba(98, 215, 255, 0.45);
}

.pet-character__motifs i:nth-child(1) { left: 12%; top: 54%; }
.pet-character__motifs i:nth-child(2) { right: 7%; top: 38%; width: 5%; }
.pet-character__motifs i:nth-child(3) { left: 24%; top: 20%; width: 4%; }
.pet-character__motifs i:nth-child(4) { right: 22%; bottom: 12%; width: 4.5%; }

.state--success .pet-character__motifs,
.state--loading .pet-character__motifs,
.state--greeting .pet-character__motifs {
  opacity: 1;
}

.state--success .pet-character__motifs i,
.state--loading .pet-character__motifs i,
.state--greeting .pet-character__motifs i {
  animation: char-motif-float 1.9s ease-in-out infinite;
}

.pet-character__motifs i:nth-child(2) { animation-delay: 180ms; }
.pet-character__motifs i:nth-child(3) { animation-delay: 360ms; }
.pet-character__motifs i:nth-child(4) { animation-delay: 520ms; }

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
}

.state--success .pet-character__sparkles i {
  animation: char-sparkle 1.15s ease-in-out infinite;
}

.state--success .pet-character__sparkles i:nth-child(2) {
  animation-delay: 120ms;
}

.state--success .pet-character__sparkles i:nth-child(3) {
  animation-delay: 240ms;
}

@keyframes char-idle {
  0%, 100% { transform: translateY(0) rotate(0deg) scale(1); }
  16% { transform: translateY(1px) rotate(-0.4deg) scale(1.012, 0.988); }
  48% { transform: translateY(-7px) rotate(0.5deg) scale(0.992, 1.012); }
  74% { transform: translateY(-2px) rotate(-0.2deg) scale(1.004, 0.996); }
}

@keyframes char-waiting {
  0%, 100% { transform: translateY(0) rotate(0) scale(1); }
  18% { transform: translateY(2px) rotate(0) scale(1.018, 0.982); }
  38% { transform: translateY(-8px) rotate(-2.4deg) scale(0.988, 1.014); }
  64% { transform: translateY(-5px) rotate(2.2deg) scale(1); }
  82% { transform: translateY(1px) rotate(-0.8deg) scale(1.01, 0.992); }
}

@keyframes char-thinking {
  0%, 100% { transform: translateY(0) rotate(0) scale(1); }
  28% { transform: translateY(-6px) rotate(-3.2deg) scale(0.992, 1.012); }
  56% { transform: translateY(-3px) rotate(2deg) scale(1); }
  78% { transform: translateY(1px) rotate(-0.8deg) scale(1.01, 0.99); }
}

@keyframes char-greeting {
  0%, 100% { transform: translateY(0) rotate(-1deg) scale(1); }
  18% { transform: translateY(2px) rotate(-2deg) scale(1.02, 0.982); }
  38% { transform: translateY(-14px) rotate(4.6deg) scale(0.984, 1.028); }
  64% { transform: translateY(0) rotate(-3.2deg) scale(1.016, 0.988); }
  82% { transform: translateY(-5px) rotate(1.4deg) scale(0.996, 1.008); }
}

@keyframes char-loading-pulse {
  0%, 100% { transform: translateY(0) scale(1); }
  22% { transform: translateY(1px) scale(1.012, 0.99); }
  52% { transform: translateY(-5px) scale(0.986, 1.012); }
  76% { transform: translateY(0) scale(1.006, 0.996); }
}

@keyframes char-studying {
  0%, 100% { transform: translateY(0) rotate(0deg) scale(1); }
  30% { transform: translateY(-5px) rotate(-1.4deg) scale(0.996, 1.008); }
  58% { transform: translateY(-2px) rotate(1.2deg) scale(1); }
  82% { transform: translateY(1px) rotate(0deg) scale(1.008, 0.994); }
}

@keyframes char-failed {
  0%, 100% { transform: translateY(7px) rotate(0) scale(1.016, 0.974); }
  22% { transform: translateY(7px) rotate(-2.2deg) scale(1.012, 0.976); }
  46% { transform: translateY(8px) rotate(2.2deg) scale(1.018, 0.972); }
  70% { transform: translateY(7px) rotate(-0.8deg) scale(1.012, 0.978); }
}

@keyframes char-success {
  0%, 100% { transform: translateY(0) rotate(0deg) scale(1); }
  14% { transform: translateY(3px) rotate(-0.8deg) scale(1.045, 0.962); }
  36% { transform: translateY(-22px) rotate(4deg) scale(0.965, 1.05); }
  58% { transform: translateY(2px) rotate(-2.4deg) scale(1.035, 0.974); }
  78% { transform: translateY(-7px) rotate(1.4deg) scale(0.992, 1.014); }
}

@keyframes char-ring { to { transform: rotate(360deg); } }

@keyframes char-ring-pulse {
  0%, 100% { filter: blur(0) drop-shadow(0 0 0 rgba(97, 225, 255, 0)); }
  50% { filter: blur(1px) drop-shadow(0 0 10px rgba(97, 225, 255, 0.48)); }
}

@keyframes char-image-breathe {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.006); }
}

@keyframes char-aura {
  0%, 100% { transform: scale(0.98) rotate(0deg); opacity: 0.52; }
  50% { transform: scale(1.05) rotate(2deg); opacity: 0.78; }
}

@keyframes char-ground {
  0%, 100% { transform: scaleX(1); opacity: 0.2; }
  50% { transform: scaleX(0.78); opacity: 0.12; }
}

@keyframes char-pop {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-5px) scale(1.08); }
}

@keyframes char-bubble {
  0%, 100% { transform: translateY(2px) scale(0.92); opacity: 0.68; }
  40% { transform: translateY(-5px) scale(1.1); opacity: 1; }
  70% { transform: translateY(-2px) scale(0.98); opacity: 0.82; }
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

@keyframes char-motif-float {
  0%, 100% { transform: translate3d(0, 3px, 0) scale(0.72); opacity: 0; }
  28% { opacity: 0.85; }
  62% { transform: translate3d(4px, -9px, 0) scale(1); opacity: 0.68; }
  100% { transform: translate3d(8px, -16px, 0) scale(0.78); opacity: 0; }
}

@keyframes char-sparkle {
  0%, 100% { transform: scale(0.45) rotate(0deg); opacity: 0; }
  34% { transform: scale(1.15) rotate(18deg); opacity: 1; }
  68% { transform: scale(0.8) rotate(38deg); opacity: 0.62; }
}

@media (prefers-reduced-motion: reduce) {
  .pet-character__stage,
  .pet-character__stage * {
    animation: none;
  }
}
</style>
