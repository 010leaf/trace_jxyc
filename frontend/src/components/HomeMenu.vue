<template>
  <div class="menu-container">
    <div class="menu-grid">
      <el-card class="menu-card" shadow="hover" @click="$emit('navigate', 'auto')">
        <div class="menu-icon">📊</div>
        <h3>自动分档</h3>
        <p>Auto Grading</p>
      </el-card>

      <el-card class="menu-card" shadow="hover" @click="$emit('navigate', 'manual')">
        <div class="menu-icon">🛠️</div>
        <h3>手动分档</h3>
        <p>Manual Grading</p>
      </el-card>

      <el-card class="menu-card" shadow="hover" @click="$emit('navigate', 'cockpit')">
        <div class="menu-icon">📤</div>
        <h3>驾驶舱上传</h3>
        <p>Cockpit Upload</p>
      </el-card>
    </div>
  </div>
</template>

<script setup>
defineOptions({
  name: 'HomeMenu'
})
defineEmits(['navigate'])
</script>

<style scoped>
.menu-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  min-height: 400px;
}

.menu-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 30px;
  width: 100%;
}

.menu-card {
  cursor: pointer;
  text-align: center;
  transition: all 0.3s;
  border-radius: 8px;
}

.menu-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0,0,0,0.1);
}

.menu-icon {
  font-size: 48px;
  margin-bottom: 20px;
}

.menu-card h3 {
  margin: 0 0 10px;
  font-size: 20px;
}

.menu-card p {
  margin: 0;
  color: #909399;
}
</style>