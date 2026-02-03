
<template>
  <div class="auto-grading">
    <div class="back-header">
      <div class="back-btn" @click="$emit('back')">
        <el-icon><ArrowLeft /></el-icon>
        <span>Back</span>
      </div>
      <h3 class="module-title">自动分档</h3>
      <div style="width: 60px;"></div> <!-- Spacer for centering -->
    </div>
    
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>数据上传与操作</span>
        </div>
      </template>
      
      <div class="upload-section">
        <el-upload
          class="upload-demo"
          action="http://localhost:8000/api/upload"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :show-file-list="true"
          accept=".xlsx"
        >
          <el-button type="primary">点击上传数据 (Excel)</el-button>
          <template #tip>
            <div class="el-upload__tip">请上传标准格式的Excel文件</div>
          </template>
        </el-upload>
      </div>

      <div class="action-section" style="margin-top: 20px;">
        <el-button type="success" @click="startAutoGrading" :loading="loading">开始自动分档</el-button>
        <el-button type="warning" @click="downloadResult" :disabled="!hasResult">下载分档结果</el-button>
      </div>
    </el-card>

      <div v-if="hasResult" class="result-section" style="margin-top: 20px;">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-card shadow="hover">
              <template #header>全市升档人数</template>
              <div class="stat-value">{{ metrics.n_up }}</div>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="hover">
              <template #header>全市降档人数</template>
              <div class="stat-value">{{ metrics.n_down }}</div>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="hover">
              <template #header>最小档位占比</template>
              <div class="stat-value">{{ (metrics.min_pct * 100).toFixed(2) }}%</div>
            </el-card>
          </el-col>
        </el-row>

        <div class="chart-section" style="margin-top: 30px;" v-if="summaryData.length > 0">
          <el-divider>各档位客户数量对比（分档前 vs 分档后）</el-divider>
          <div class="chart-container">
            <Bar :data="comparisonChartData" :options="chartOptions" />
          </div>
        </div>

        <el-divider>分档明细 (前50条)</el-divider>
        <el-table :data="top50" style="width: 100%" height="400">
        <el-table-column prop="许可证号" label="许可证号" width="180" />
        <el-table-column prop="所属区县" label="所属区县" width="120" />
        <el-table-column prop="原档位" label="原档位" width="100" />
        <el-table-column prop="新档位" label="新档位" width="100" />
        <el-table-column prop="总分" label="总分" width="100" />
        <el-table-column prop="总分排名" label="排名" width="100" />
        <el-table-column prop="卷烟购进金额得分" label="购进得分" width="120" />
        <el-table-column prop="卷烟非购进金额得分" label="非购进得分" width="120" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
defineOptions({
  name: 'AutoGrading'
})
import { ref, computed } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const loading = ref(false)
const hasResult = ref(false)
const metrics = ref({})
const top50 = ref([])
const summaryData = ref([])

const handleUploadSuccess = (response) => {
  ElMessage.success('数据上传成功')
}

const handleUploadError = (error) => {
  ElMessage.error('上传失败: ' + error.message)
}

const startAutoGrading = async () => {
  loading.value = true
  try {
    const res = await axios.post('http://localhost:8000/api/auto-grade')
    metrics.value = res.data.metrics
    top50.value = res.data.top50
    summaryData.value = res.data.summary
    hasResult.value = true
    ElMessage.success('自动分档完成')
    
    // Store metrics for manual grading to use
    localStorage.setItem('grading_summary', JSON.stringify(res.data.summary))
  } catch (error) {
    ElMessage.error('分档计算失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const downloadResult = async () => {
  try {
    const response = await axios.get('http://localhost:8000/api/download', {
      responseType: 'blob'
    })
    
    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'auto_grading_result.xlsx')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error('下载失败: ' + error.message)
  }
}

const comparisonChartData = computed(() => {
  if (summaryData.value.length === 0) return null
  
  // Sort grades (usually they come 30 down to 1, let's reverse for chart 1 to 30 or keep as is)
  // Let's sort by Grade Number Ascending (1 to 30) for better view
  const sorted = [...summaryData.value].sort((a, b) => a.Grade - b.Grade)
  
  const labels = sorted.map(item => item.GradeName)
  const newCounts = sorted.map(item => item.Count)
  // We need old counts. But summaryData only has new counts?
  // Wait, backend generate_summary function in grading_utils.py only puts New Count?
  // Let's check backend. Yes, generate_summary only has 'Count' (New).
  // generate_export_data has '分档前_客户数'.
  // But /api/auto-grade returns `grading_utils.generate_summary(best_df)` which is the simpler one.
  // We need to update `generate_summary` in backend to include Old Counts or use `generate_export_data` logic.
  // Actually, for chart, we need Old Counts.
  // Since we can't easily change backend structure without breaking manual grading potentially,
  // Let's update `generate_summary` to include `OldCount` if possible.
  
  // Assuming backend is updated to return `OldCount` or `PreCount`.
  // If not available, we can't show it.
  // Let's modify backend `generate_summary` first.
  const oldCounts = sorted.map(item => item.PreCount || 0) 
  
  return {
    labels: labels,
    datasets: [
      {
        label: '分档前人数',
        backgroundColor: '#909399',
        data: oldCounts
      },
      {
        label: '分档后人数',
        backgroundColor: '#409EFF',
        data: newCounts
      }
    ]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top',
    },
    title: {
      display: true,
      text: '各档位客户分布对比'
    }
  }
}
</script>

<style scoped>
.auto-grading {
  padding: 20px;
  min-height: 100vh;
  background-image: linear-gradient(to top, #cfd9df 0%, #e2ebf0 100%);
}

.el-card {
  background-color: rgba(255, 255, 255, 0.9) !important;
}

.back-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 20px;
  background: linear-gradient(135deg, #409EFF 0%, #337ecc 100%);
  color: white;
  border-radius: 8px 8px 0 0;
  margin-bottom: 20px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  background-color: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.4);
  color: white;
  padding: 6px 15px;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 14px;
}

.back-btn:hover {
  background-color: rgba(255, 255, 255, 0.3);
}

.module-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #409EFF;
  text-align: center;
}
.chart-container {
  height: 400px;
  margin-bottom: 30px;
}
</style>
