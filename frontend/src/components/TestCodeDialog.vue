<template>
  <el-dialog
    v-model="visible"
    :title="testCase?.name"
    width="80%"
    class="test-code-dialog"
    @close="handleClose"
  >
    <div class="test-code-content">
      <!-- 测试信息头部 -->
      <div class="test-header">
        <div class="test-meta">
          <el-tag :type="getTestTypeColor(testCase?.type)">
            {{ testCase?.type }}
          </el-tag>
          <el-tag :type="getPriorityColor(testCase?.priority)" effect="plain">
            {{ testCase?.priority }}
          </el-tag>
          <span class="confidence">置信度: {{ (testCase?.confidence * 100).toFixed(1) }}%</span>
        </div>
        
        <div class="test-actions">
          <el-button size="small" @click="copyCode">
            <el-icon><CopyDocument /></el-icon>
            复制代码
          </el-button>
          <el-button size="small" @click="formatCode">
            <el-icon><Magic /></el-icon>
            格式化
          </el-button>
          <el-button size="small" type="primary" @click="runTest">
            <el-icon><CaretRight /></el-icon>
            运行测试
          </el-button>
        </div>
      </div>
      
      <!-- 测试描述 -->
      <div class="test-description">
        <h4>测试描述</h4>
        <p>{{ testCase?.description }}</p>
      </div>
      
      <!-- 代码编辑器 -->
      <div class="test-code-editor">
        <h4>测试代码</h4>
        <CodeEditor
          ref="codeEditorRef"
          v-model="editableCode"
          :language="getLanguageFromTestType(testCase?.type)"
          :height="'350px'"
          :readonly="!editable"
          :options="editorOptions"
          @change="onCodeChange"
        />
      </div>
      
      <!-- 前置条件 -->
      <div v-if="testCase?.prerequisites?.length" class="test-prerequisites">
        <h4>前置条件</h4>
        <ul>
          <li v-for="prerequisite in testCase.prerequisites" :key="prerequisite">
            {{ prerequisite }}
          </li>
        </ul>
      </div>
      
      <!-- 执行结果 -->
      <div v-if="executionResult" class="execution-result">
        <h4>执行结果</h4>
        <div class="result-content" :class="executionResult.status">
          <div class="result-status">
            <el-icon v-if="executionResult.status === 'success'" class="status-icon"><CircleCheck /></el-icon>
            <el-icon v-else-if="executionResult.status === 'error'" class="status-icon"><CircleClose /></el-icon>
            <el-icon v-else class="status-icon"><Loading /></el-icon>
            <span>{{ getStatusText(executionResult.status) }}</span>
          </div>
          
          <div v-if="executionResult.output" class="result-output">
            <CodeEditor
              :model-value="executionResult.output"
              language="text"
              :height="'150px'"
              :readonly="true"
              :options="{ minimap: { enabled: false } }"
            />
          </div>
        </div>
      </div>
    </div>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">关闭</el-button>
        <el-button v-if="editable && hasChanges" type="primary" @click="saveChanges">
          保存修改
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  CopyDocument, Magic, CaretRight, CircleCheck, 
  CircleClose, Loading 
} from '@element-plus/icons-vue'
import CodeEditor from './CodeEditor.vue'
import { copyToClipboard } from '@/utils/helpers'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  testCase: {
    type: Object,
    default: null
  },
  editable: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'save', 'run'])

const codeEditorRef = ref(null)
const editableCode = ref('')
const executionResult = ref(null)
const hasChanges = ref(false)

// 计算属性
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// 编辑器选项
const editorOptions = {
  fontSize: 13,
  lineNumbers: 'on',
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  wordWrap: 'on',
  tabSize: 2,
  insertSpaces: true,
  formatOnPaste: true,
  formatOnType: true
}

// 监听测试用例变化
watch(() => props.testCase, (newTestCase) => {
  if (newTestCase) {
    editableCode.value = newTestCase.code || ''
    hasChanges.value = false
    executionResult.value = null
  }
}, { immediate: true })

// 代码变化处理
const onCodeChange = (code) => {
  hasChanges.value = code !== (props.testCase?.code || '')
}

// 方法
const handleClose = () => {
  if (hasChanges.value) {
    ElMessage.confirm('有未保存的修改，确定要关闭吗？')
      .then(() => {
        visible.value = false
      })
      .catch(() => {})
  } else {
    visible.value = false
  }
}

const copyCode = async () => {
  try {
    await copyToClipboard(editableCode.value)
    ElMessage.success('代码已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

const formatCode = () => {
  if (codeEditorRef.value) {
    const editor = codeEditorRef.value.getEditor()
    if (editor) {
      editor.getAction('editor.action.formatDocument').run()
    }
  }
}

const runTest = async () => {
  try {
    executionResult.value = { status: 'running', output: '' }
    
    const result = await emit('run', {
      ...props.testCase,
      code: editableCode.value
    })
    
    executionResult.value = result
  } catch (error) {
    executionResult.value = {
      status: 'error',
      output: error.message || '执行失败'
    }
  }
}

const saveChanges = () => {
  emit('save', {
    ...props.testCase,
    code: editableCode.value
  })
  hasChanges.value = false
  ElMessage.success('保存成功')
}

// 辅助方法
const getTestTypeColor = (type) => {
  const colorMap = {
    'unit': 'success',
    'integration': 'warning',
    'e2e': 'danger'
  }
  return colorMap[type] || 'info'
}

const getPriorityColor = (priority) => {
  const colorMap = {
    'high': 'danger',
    'medium': 'warning',
    'low': 'success'
  }
  return colorMap[priority] || 'info'
}

const getLanguageFromTestType = (type) => {
  // 根据测试类型返回对应的语言
  return 'javascript' // 默认JavaScript，可以根据项目配置调整
}

const getStatusText = (status) => {
  const statusMap = {
    'running': '执行中...',
    'success': '执行成功',
    'error': '执行失败'
  }
  return statusMap[status] || status
}
</script>

<style lang="scss" scoped>
.test-code-dialog {
  .test-code-content {
    .test-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      padding-bottom: 15px;
      border-bottom: 1px solid #ebeef5;
      
      .test-meta {
        display: flex;
        align-items: center;
        gap: 10px;
        
        .confidence {
          color: #606266;
          font-size: 13px;
        }
      }
      
      .test-actions {
        display: flex;
        gap: 8px;
      }
    }
    
    .test-description {
      margin-bottom: 20px;
      
      h4 {
        margin: 0 0 8px 0;
        color: #303133;
        font-size: 14px;
      }
      
      p {
        margin: 0;
        color: #606266;
        line-height: 1.6;
      }
    }
    
    .test-code-editor {
      margin-bottom: 20px;
      
      h4 {
        margin: 0 0 12px 0;
        color: #303133;
        font-size: 14px;
      }
    }
    
    .test-prerequisites {
      margin-bottom: 20px;
      
      h4 {
        margin: 0 0 8px 0;
        color: #303133;
        font-size: 14px;
      }
      
      ul {
        margin: 0;
        padding-left: 20px;
        
        li {
          margin-bottom: 4px;
          color: #606266;
          font-size: 13px;
        }
      }
    }
    
    .execution-result {
      h4 {
        margin: 0 0 12px 0;
        color: #303133;
        font-size: 14px;
      }
      
      .result-content {
        border: 1px solid #ebeef5;
        border-radius: 4px;
        padding: 12px;
        
        &.success {
          border-color: #67c23a;
          background-color: #f0f9ff;
        }
        
        &.error {
          border-color: #f56c6c;
          background-color: #fef0f0;
        }
        
        &.running {
          border-color: #e6a23c;
          background-color: #fdf6ec;
        }
        
        .result-status {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 8px;
          font-size: 13px;
          font-weight: 500;
          
          .status-icon {
            font-size: 16px;
          }
        }
        
        .result-output {
          margin-top: 8px;
        }
      }
    }
  }
  
  .dialog-footer {
    text-align: right;
    
    .el-button {
      margin-left: 8px;
    }
  }
}
</style>