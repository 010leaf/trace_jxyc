
<template>
  <div class="manual-grading">
    <div class="back-header">
      <div class="back-btn" @click="$emit('back')">
        <el-icon><ArrowLeft /></el-icon>
        <span>Back</span>
      </div>
      <h3 class="module-title">手动分档</h3>
      <div style="width: 60px;"></div>
    </div>

    <el-card class="main-card">
      <div v-if="summary.length === 0" class="empty-tip">
        请先在“自动分档”模块完成计算。
      </div>

      <div v-else>
        <el-alert
          title="说明：请在下方调整各档位的最低分数线，表格和图表将实时更新预览。确认无误后点击“应用手动分档”保存。"
          type="info"
          show-icon
          style="margin-bottom: 20px;"
        />
        
        <el-row :gutter="20">
          <!-- Left Column: Table & Controls -->
          <el-col :span="10">
            <h3>分数线调整</h3>
            <el-table :data="editableSummary" height="600" border stripe>
              <el-table-column prop="Grade" label="档位" width="70" align="center" fixed />
              <el-table-column label="最低分数线" min-width="140">
                <template #default="scope">
                  <el-input-number 
                    v-model="scope.row.MinScore" 
                    :precision="4" 
                    :step="0.1" 
                    size="small" 
                    style="width: 100%"
                    @change="handleThresholdChange"
                  />
                </template>
              </el-table-column>
              <el-table-column label="当前人数" width="90" align="center">
                <template #default="scope">
                   <span :style="{ color: scope.row.Count !== getOriginalCount(scope.row.Grade) ? '#E6A23C' : 'inherit', fontWeight: scope.row.Count !== getOriginalCount(scope.row.Grade) ? 'bold' : 'normal' }">
                     {{ scope.row.Count }}
                   </span>
                </template>
              </el-table-column>
              <el-table-column label="原人数" width="80" align="center">
                <template #default="scope">
                  {{ getOriginalCount(scope.row.Grade) }}
                </template>
              </el-table-column>
              <el-table-column label="升档%" width="80" align="center">
                <template #default="scope">
                  <span style="color: #67C23A">{{ (scope.row.UpgradeRate * 100).toFixed(1) }}%</span>
                </template>
              </el-table-column>
              <el-table-column label="降档%" width="80" align="center">
                <template #default="scope">
                  <span style="color: #F56C6C">{{ (scope.row.DowngradeRate * 100).toFixed(1) }}%</span>
                </template>
              </el-table-column>
            </el-table>
            <div style="margin-top: 20px; text-align: center;">
              <el-button type="primary" size="large" @click="applyManualGrading" :loading="loading">应用手动分档</el-button>
              <el-button type="warning" size="large" @click="downloadResult">下载结果</el-button>
            </div>
          </el-col>
          
          <!-- Right Column: Overview Charts -->
          <el-col :span="14">
            <el-row :gutter="10">
                <el-col :span="24">
                    <h3>分布预览 (实时对比)</h3>
                    <!-- Original vs Current Count Chart -->
                    <div class="chart-container" style="height: 300px; margin-bottom: 20px;">
                      <Bar v-if="chartData" :data="chartData" :options="chartOptions" />
                    </div>
                </el-col>
            </el-row>
            
            <el-row :gutter="20">
                <el-col :span="12">
                    <h3>升降档占比 (按档位)</h3>
                    <!-- Upgrade/Downgrade Rate Chart -->
                    <div class="chart-container" style="height: 250px;">
                      <Bar v-if="rateChartData" :data="rateChartData" :options="rateChartOptions" />
                    </div>
                </el-col>
                <el-col :span="12">
                    <h3>各区县总况</h3>
                    <!-- District Stats Chart -->
                    <div class="chart-container" style="height: 250px;">
                      <Bar v-if="districtChartData" :data="districtChartData" :options="districtChartOptions" />
                    </div>
                </el-col>
            </el-row>
          </el-col>
        </el-row>

        <el-divider content-position="left"><span style="font-size: 16px; font-weight: bold; color: #409EFF;">各区县详细分布 (实时联动)</span></el-divider>

        <!-- Per District Charts Grid -->
        <el-row :gutter="20">
            <el-col :span="8" v-for="item in districtDetailCharts" :key="item.name" style="margin-bottom: 20px;">
                <el-card shadow="hover" :body-style="{ padding: '10px' }" class="district-card">
                    <template #header>
                        <div class="district-header">
                            <span>{{ item.name }}</span>
                        </div>
                    </template>
                    <div class="chart-container" style="height: 220px;">
                        <Bar v-if="item.data" :data="item.data" :options="perDistrictChartOptions" />
                    </div>
                </el-card>
            </el-col>
        </el-row>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { Bar, Line } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, LineElement, PointElement, CategoryScale, LinearScale } from 'chart.js'
import ChartDataLabels from 'chartjs-plugin-datalabels'
import { debounce } from 'lodash'

ChartJS.register(Title, Tooltip, Legend, BarElement, LineElement, PointElement, CategoryScale, LinearScale, ChartDataLabels)

const summary = ref([]) // Original summary (Baseline)
const editableSummary = ref([]) // Current editable summary (Preview)
const districtStats = ref([]) // New District Stats
const districtDetail = ref({}) // New District Detail (Per Grade)
const loading = ref(false)

const fetchData = () => {
  const stored = localStorage.getItem('grading_summary')
  if (stored) {
    summary.value = JSON.parse(stored)
    // Deep copy for editing
    editableSummary.value = JSON.parse(stored).map(item => ({...item}))
  } else {
    ElMessage.warning('未找到分档数据，请先进行自动分档')
  }
}

// Initial fetch of district stats if possible, or wait for preview?
// Since auto-grade returns district_stats now, we should store it too.
// But we might not have it in localStorage from old saves.
// Let's trigger a preview on mount to get full data including district stats if missing.
onMounted(async () => {
  fetchData()
  // Trigger an initial preview to populate UpgradeRate/DowngradeRate and DistrictStats 
  // if they are missing from localStorage data (which might be old format)
  if (editableSummary.value.length > 0) {
      await debouncedPreview()
  }
})

const getOriginalCount = (grade) => {
  const original = summary.value.find(item => item.Grade === grade)
  return original ? original.PreCount : 0
}

// Debounce the preview call to avoid too many requests
const debouncedPreview = debounce(async () => {
  try {
    const thresholds = {}
    editableSummary.value.forEach(item => {
       thresholds[item.Grade] = item.MinScore
    })
    
    const res = await axios.post('http://localhost:8000/api/preview-manual-grade', { thresholds })
    
    const previewData = res.data.summary
    districtStats.value = res.data.district_stats || []
    districtDetail.value = res.data.district_detail || {}
    
    // Update editableSummary
    editableSummary.value.forEach(item => {
      const pItem = previewData.find(p => p.Grade === item.Grade)
      if (pItem) {
        item.Count = pItem.Count
        item.UpgradeRate = pItem.UpgradeRate || 0
        item.DowngradeRate = pItem.DowngradeRate || 0
      }
    })
    
  } catch (error) {
    console.error("Preview failed", error)
  }
}, 500)

const handleThresholdChange = () => {
  debouncedPreview()
}

const applyManualGrading = async () => {
  loading.value = true
  try {
    // Construct thresholds dict
    const thresholds = {}
    editableSummary.value.forEach(item => {
        thresholds[item.Grade] = item.MinScore
    })

    const res = await axios.post('http://localhost:8000/api/manual-grade', { thresholds })
    
    // Update baseline to the new applied state
    summary.value = res.data.summary
    localStorage.setItem('grading_summary', JSON.stringify(res.data.summary))
    
    // Refresh editable to match perfectly
    editableSummary.value = res.data.summary.map(item => ({...item}))
    
    ElMessage.success('手动分档已应用')
  } catch (error) {
    ElMessage.error('应用失败: ' + (error.response?.data?.detail || error.message))
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
    link.setAttribute('download', 'manual_grading_result.xlsx')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error('下载失败: ' + error.message)
  }
}

    // Chart Data
const chartData = computed(() => {
  if (summary.value.length === 0) return null
  
  // Sort 1-30 for chart
  const sortedOriginal = [...summary.value].sort((a, b) => a.Grade - b.Grade)
  const sortedCurrent = [...editableSummary.value].sort((a, b) => a.Grade - b.Grade)
  
  const labels = sortedOriginal.map(item => item.GradeName)
  // Use PreCount for the "Original" dataset to match user requirement (Raw Uploaded Data)
  const originalData = sortedOriginal.map(item => item.PreCount) 
  const currentData = sortedCurrent.map(item => item.Count)
  
  return {
    labels: labels,
    datasets: [
      {
        label: '原方案人数', // Raw Uploaded Data
        backgroundColor: '#909399',
        data: originalData
      },
      {
        label: '当前预览人数', // Live Preview (Manual Adjusted)
        backgroundColor: '#E6A23C',
        data: currentData
      }
    ]
  }
})

// New Chart: Rate Chart (Upgrade/Downgrade %)
const rateChartData = computed(() => {
  if (editableSummary.value.length === 0) return null
  
  const sorted = [...editableSummary.value].sort((a, b) => a.Grade - b.Grade)
  const labels = sorted.map(item => item.GradeName)
  
  // Convert to percentage 0-100
  const upRates = sorted.map(item => (item.UpgradeRate || 0) * 100)
  const downRates = sorted.map(item => (item.DowngradeRate || 0) * 100)
  
  return {
    labels: labels,
    datasets: [
      {
        label: '升档占比 (%)',
        backgroundColor: '#67C23A',
        data: upRates
      },
      {
        label: '降档占比 (%)',
        backgroundColor: '#F56C6C',
        data: downRates
      }
    ]
  }
})

// New Chart: District Stats (Enhanced with Lines)
const districtChartData = computed(() => {
  if (districtStats.value.length === 0) return null
  
  const labels = districtStats.value.map(d => d.District)
  const upCounts = districtStats.value.map(d => d.Upgrades)
  const downCounts = districtStats.value.map(d => d.Downgrades)
  const upRates = districtStats.value.map(d => (d.UpgradeRate * 100).toFixed(1))
  const downRates = districtStats.value.map(d => (d.DowngradeRate * 100).toFixed(1))
  
  return {
    labels: labels,
    datasets: [
      {
        type: 'bar',
        label: '升档数量',
        backgroundColor: '#409EFF',
        data: upCounts,
        yAxisID: 'y',
        datalabels: {
            display: false
        }
      },
      {
        type: 'bar',
        label: '降档数量',
        backgroundColor: '#F56C6C',
        data: downCounts,
        yAxisID: 'y',
        datalabels: {
            display: false
        }
      },
      {
        type: 'line',
        label: '升档率(%)',
        borderColor: '#1f77b4', // Darker Blue
        backgroundColor: '#1f77b4',
        data: upRates,
        yAxisID: 'y1',
        tension: 0.1,
        datalabels: {
            align: 'top',
            anchor: 'end',
            color: '#1f77b4',
            font: { weight: 'bold' },
            formatter: (value) => value + '%'
        }
      },
      {
        type: 'line',
        label: '降档率(%)',
        borderColor: '#d62728', // Darker Red
        backgroundColor: '#d62728',
        data: downRates,
        yAxisID: 'y1',
        tension: 0.1,
        datalabels: {
            align: 'bottom',
            anchor: 'start',
            color: '#d62728',
            font: { weight: 'bold' },
            formatter: (value) => value + '%'
        }
      }
    ]
  }
})

// New: Per District Charts Data Generator
const districtDetailCharts = computed(() => {
    if (!districtDetail.value) return []
    
    const sortOrder = ['南湖', '秀洲', '市区', '嘉善', '平湖', '海宁', '海盐', '桐乡']
    const tempMap = {}

    for (const [district, data] of Object.entries(districtDetail.value)) {
        // data is list of { Grade, Count, Upgrades, Downgrades }
        // Ensure sorted by Grade
        const sortedData = [...data].sort((a, b) => a.Grade - b.Grade)
        const labels = sortedData.map(item => item.Grade + '档')
        
        // Calculate Percentages
        const upPcts = sortedData.map(item => item.Count > 0 ? ((item.Upgrades / item.Count) * 100).toFixed(1) : 0)
        const downPcts = sortedData.map(item => item.Count > 0 ? ((item.Downgrades / item.Count) * 100).toFixed(1) : 0)
        const totalCounts = sortedData.map(item => item.Count)
        
        tempMap[district] = {
            labels: labels,
            datasets: [
                {
                    type: 'bar',
                    label: '升档占比(%)',
                    backgroundColor: '#67C23A',
                    data: upPcts,
                    yAxisID: 'y',
                    datalabels: { display: false } // Hide labels on bars
                },
                {
                    type: 'bar',
                    label: '降档占比(%)',
                    backgroundColor: '#F56C6C',
                    data: downPcts,
                    yAxisID: 'y',
                    datalabels: { display: false } // Hide labels on bars
                },
                {
                    type: 'line',
                    label: '该档总人数',
                    borderColor: '#E6A23C',
                    borderWidth: 2,
                    pointRadius: 3,
                    data: totalCounts,
                    yAxisID: 'y1', // Use separate axis for total
                    datalabels: {
                        display: false, // Hide labels for line too
                        align: 'top',
                        color: '#E6A23C',
                        font: { size: 10 },
                        formatter: (value) => value // Just number
                    }
                }
            ]
        }
    }

    // Sort keys based on sortOrder
    const sortedKeys = Object.keys(tempMap).sort((a, b) => {
        const idxA = sortOrder.indexOf(a)
        const idxB = sortOrder.indexOf(b)
        // If not found (-1), put at end
        if (idxA === -1 && idxB === -1) return a.localeCompare(b)
        if (idxA === -1) return 1
        if (idxB === -1) return -1
        return idxA - idxB
    })

    return sortedKeys.map(key => ({
        name: key,
        data: tempMap[key]
    }))
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
      datalabels: { display: false } // Disable global datalabels for this chart unless specified
  }
}

const rateChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
      datalabels: { display: false }
  },
  scales: {
      y: {
          beginAtZero: true,
          title: {
              display: true,
              text: '占比 (%)'
          }
      }
  }
}

const districtChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
      // Datalabels config handled in dataset
  },
  scales: {
      y: {
          beginAtZero: true,
          type: 'linear',
          position: 'left',
          title: { display: true, text: '数量 (人)' }
      },
      y1: {
          beginAtZero: true,
          type: 'linear',
          position: 'right',
          title: { display: true, text: '比率 (%)' },
          grid: { drawOnChartArea: false }
      }
  }
}

const perDistrictChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
      datalabels: { display: false }, // Force hide datalabels globally for this chart
      tooltip: {
          callbacks: {
              label: function(context) {
                  let label = context.dataset.label || '';
                  if (label) {
                      label += ': ';
                  }
                  if (context.parsed.y !== null) {
                      label += context.parsed.y;
                      if (context.dataset.type === 'bar') label += '%';
                  }
                  return label;
              }
          }
      }
  },
  scales: {
      y: {
          beginAtZero: true,
          title: { display: true, text: '占比 (%)' },
          max: 100
      },
      y1: {
          beginAtZero: true,
          position: 'right',
          title: { display: true, text: '总人数' },
          grid: { drawOnChartArea: false }
      }
  }
}
</script>

<style scoped>
.manual-grading {
  padding: 20px;
  min-height: 100vh;
  background-image: linear-gradient(to top, #cfd9df 0%, #e2ebf0 100%);
}

.main-card {
  background-color: rgba(255, 255, 255, 0.95) !important;
}

.district-card {
  background-color: rgba(255, 255, 255, 0.9) !important;
}

.back-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 20px;
  background: linear-gradient(135deg, #E6A23C 0%, #d48e26 100%);
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

.chart-container {
  height: 400px;
}
.empty-tip {
  text-align: center;
  color: #909399;
  padding: 50px;
}
</style>
