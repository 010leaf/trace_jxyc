
<template>
  <div class="cockpit-upload">
    <div class="back-header">
      <div class="back-btn" @click="$emit('back')">
        <el-icon><ArrowLeft /></el-icon>
        <span>Back</span>
      </div>
      <h3 class="module-title">驾驶舱数据上传</h3>
      <div class="header-actions">
         <el-button link type="primary" @click="openCockpit" class="cockpit-link">
            访问驾驶舱 <el-icon class="el-icon--right"><TopRight /></el-icon>
         </el-button>
      </div>
    </div>

    <el-card>
      <div class="upload-area">
        <el-form :inline="true">
          <el-form-item label="数据日期">
            <el-date-picker
              v-model="uploadDate"
              type="month"
              placeholder="选择月份"
              format="YYYY-MM"
              value-format="YYYYMM"
              :clearable="false"
            />
          </el-form-item>
        </el-form>
        
        <el-upload
          class="upload-demo"
          drag
          action=""
          :http-request="uploadFile"
          :show-file-list="false"
          accept=".xlsx"
          :disabled="uploading"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            拖拽文件到此处或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              请上传包含“明细表”和“汇总表”的Excel文件 (.xlsx)
            </div>
          </template>
        </el-upload>

        <div v-if="uploading" class="progress-container">
           <el-progress 
             :percentage="progress" 
             :status="progressStatus"
             :format="progressFormat"
           />
           <div class="loading-text">{{ loadingText }}</div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { UploadFilled, ArrowLeft, TopRight } from '@element-plus/icons-vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const openCockpit = () => {
  window.open('https://192.168.113.14/ycfdJsc/index.html', '_blank')
}

const uploadDate = ref(dayjs().format('YYYYMM'))
const uploading = ref(false)
const progress = ref(0)
const loadingText = ref('准备上传...')
const progressStatus = ref('')

const progressFormat = (percentage) => {
  return percentage === 100 ? '处理中' : `${percentage}%`
}

const uploadFile = async (options) => {
  const formData = new FormData()
  formData.append('file', options.file)
  formData.append('date', uploadDate.value)

  uploading.value = true
  progress.value = 0
  progressStatus.value = ''
  loadingText.value = '正在上传...'

  try {
    const res = await axios.post('http://localhost:8000/api/cockpit-upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        progress.value = percentCompleted
        if (percentCompleted === 100) {
           loadingText.value = '上传完成，正在写入数据库（请勿关闭）...'
        }
      }
    })
    
    progressStatus.value = 'success'
    loadingText.value = '处理完成！'
    ElMessage.success(res.data.message)
  } catch (error) {
    progressStatus.value = 'exception'
    loadingText.value = '上传失败'
    ElMessage.error('上传失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    // Reset after a delay
    setTimeout(() => {
      uploading.value = false
      progress.value = 0
      loadingText.value = ''
      progressStatus.value = ''
    }, 3000)
  }
}
</script>

<style scoped>
.cockpit-upload {
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
  background: linear-gradient(135deg, #67C23A 0%, #529b2e 100%);
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

.cockpit-link {
  color: white !important;
  font-weight: 500;
}

.cockpit-link:hover {
  opacity: 0.9;
  text-decoration: underline;
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
}
.upload-demo {
  width: 100%;
  max-width: 500px;
}
.progress-container {
  width: 100%;
  max-width: 500px;
  margin-top: 20px;
}
.loading-text {
  text-align: center;
  margin-top: 5px;
  color: #606266;
  font-size: 14px;
}
</style>
