<template>
  <div class="app-container">
    <header class="app-header" v-if="currentView === 'menu'">
      <h1>烟草分档项目</h1>
      <p>Tobacco Grading System</p>
    </header>

    <main class="app-main">
        <transition name="fade" mode="out-in">
          <keep-alive include="AutoGrading">
            <component 
              :is="currentComponent" 
              @back="currentView = 'menu'" 
              @navigate="handleNavigate"
            />
          </keep-alive>
        </transition>
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import AutoGrading from './components/AutoGrading.vue'
import ManualGrading from './components/ManualGrading.vue'
import CockpitUpload from './components/CockpitUpload.vue'
import HomeMenu from './components/HomeMenu.vue'

const currentView = ref('menu')

const currentComponent = computed(() => {
  switch (currentView.value) {
    case 'auto': return AutoGrading
    case 'manual': return ManualGrading
    case 'cockpit': return CockpitUpload
    default: return HomeMenu
  }
})

const handleNavigate = (view) => {
  currentView.value = view
}
</script>

<style>
/* Reset & Base */
body {
  margin: 0;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  background-color: #f5f7fa;
  color: #303133;
}

.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  text-align: center;
  padding: 40px 0 20px;
  background: #fff;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  margin-bottom: 20px;
}

.app-header h1 {
  margin: 0;
  font-size: 28px;
  color: #409EFF;
}

.app-header p {
  margin: 10px 0 0;
  color: #909399;
}

.app-main {
  flex: 1;
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

/* Transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>