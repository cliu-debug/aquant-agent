<template>
  <g class="workflow-edge">
    <line
      :x1="x1"
      :y1="y1"
      :x2="x2"
      :y2="y2"
      class="edge-bg"
    />
    <line
      :x1="x1"
      :y1="y1"
      :x2="x2"
      :y2="y2"
      class="edge-line"
      :class="{
        'is-active': active,
        'is-animated': animated,
      }"
    />
  </g>
</template>

<script setup lang="ts">
defineProps<{
  /** 起点 X 坐标 */
  x1: number
  /** 起点 Y 坐标 */
  y1: number
  /** 终点 X 坐标 */
  x2: number
  /** 终点 Y 坐标 */
  y2: number
  /** 是否激活（发光） */
  active: boolean
  /** 是否动画（虚线流动） */
  animated: boolean
}>()
</script>

<style scoped>
.edge-bg {
  stroke: rgba(71, 85, 105, 0.3);
  stroke-width: 3;
  stroke-linecap: round;
}

.edge-line {
  stroke: #475569;
  stroke-width: 2;
  stroke-linecap: round;
  transition: stroke 0.4s ease, stroke-width 0.4s ease, filter 0.4s ease;
}

.edge-line.is-active {
  stroke: #3b82f6;
  stroke-width: 2.5;
  filter: drop-shadow(0 0 6px rgba(59, 130, 246, 0.5));
}

.edge-line.is-animated {
  stroke-dasharray: 8 4;
  animation: dash-flow 0.8s linear infinite;
}

.edge-line.is-active.is-animated {
  stroke: #60a5fa;
  stroke-dasharray: 8 4;
  animation: dash-flow 0.6s linear infinite;
  filter: drop-shadow(0 0 8px rgba(96, 165, 250, 0.6));
}

@keyframes dash-flow {
  from {
    stroke-dashoffset: 12;
  }
  to {
    stroke-dashoffset: 0;
  }
}
</style>
