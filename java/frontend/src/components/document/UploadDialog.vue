<template>
  <el-dialog
    v-model="visible"
    title="上传文档"
    width="480px"
    @close="resetForm"
  >
    <el-form ref="formRef" :model="form" label-position="top">
      <el-form-item label="标题" required>
        <el-input v-model="form.title" placeholder="文档标题" />
      </el-form-item>
      <el-form-item label="文件" required>
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :limit="1"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
          :before-upload="beforeUpload"
          accept=".pdf,.md,.txt,.docx"
          drag
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">拖拽文件至此或点击上传</div>
          <template #tip>
            <div class="el-upload__tip">
              支持 PDF / MD / TXT / DOCX，≤ 50MB
            </div>
          </template>
        </el-upload>
      </el-form-item>
      <el-form-item label="部门">
        <el-select v-model="form.department" class="w-full">
          <el-option label="全部" value="全部" />
          <el-option label="技术部" value="技术部" />
          <el-option label="产品部" value="产品部" />
          <el-option label="人事部" value="人事部" />
          <el-option label="财务部" value="财务部" />
          <el-option label="法务部" value="法务部" />
        </el-select>
      </el-form-item>
      <el-form-item label="安全级别">
        <el-radio-group v-model="form.securityLevel">
          <el-radio value="公开">公开</el-radio>
          <el-radio value="内部">内部</el-radio>
          <el-radio value="机密">机密</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="uploading" @click="handleUpload">
        上传
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import type { UploadFile } from 'element-plus'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  upload: [file: File, title: string, department: string, securityLevel: string]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v: boolean) => emit('update:modelValue', v)
})

const uploading = ref(false)
const formRef = ref()
const uploadRef = ref()

const form = reactive({
  title: '',
  department: '全部',
  securityLevel: '内部'
})

let selectedFile: File | null = null

const ALLOWED_TYPES = ['pdf', 'md', 'txt', 'docx']
const MAX_SIZE = 50 * 1024 * 1024

function beforeUpload(file: File): boolean {
  const ext = file.name.split('.').pop()?.toLowerCase() || ''
  if (!ALLOWED_TYPES.includes(ext)) {
    ElMessage.error('不支持的文件类型，仅支持 PDF / MD / TXT / DOCX')
    return false
  }
  if (file.size > MAX_SIZE) {
    ElMessage.error('文件大小不能超过 50MB')
    return false
  }
  return false // prevent auto upload, we handle it manually
}

function handleFileChange(file: UploadFile) {
  if (file.raw) {
    selectedFile = file.raw
  }
}

function handleFileRemove() {
  selectedFile = null
}

async function handleUpload() {
  if (!form.title.trim()) {
    ElMessage.warning('请输入文档标题')
    return
  }
  if (!selectedFile) {
    ElMessage.warning('请选择文件')
    return
  }

  uploading.value = true
  try {
    emit('upload', selectedFile, form.title, form.department, form.securityLevel)
  } finally {
    uploading.value = false
  }
}

function resetForm() {
  form.title = ''
  form.department = '全部'
  form.securityLevel = '内部'
  selectedFile = null
  uploadRef.value?.clearFiles()
}
</script>

<style scoped>
.w-full { width: 100%; }
</style>
