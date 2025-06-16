<template>
  <div class="diff-editor-container">
    <div class="diff-header" v-if="showHeader">
      <div class="file-info">
        <el-icon><Document /></el-icon>
        <span class="file-path">{{ filePath }}</span>
      </div>
      <div class="diff-stats">
        <span class="additions">+{{ additions }}</span>
        <span class="deletions">-{{ deletions }}</span>
      </div>
    </div>
    
    <div 
      ref="diffContainer" 
      class="monaco-diff-editor"
      :style="{ height: height }"
    ></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as monaco from 'monaco-editor'
import { Document } from '@element-plus/icons-vue'

const props = defineProps({
  originalCode: {
    type: String,
    default: ''
  },
  modifiedCode: {
    type: String,
    default: ''
  },
  language: {
    type: String,
    default: 'javascript'
  },
  filePath: {
    type: String,
    default: ''
  },
  height: {
    type: String,
    default: '400px'
  },
  showHeader: {
    type: Boolean,
    default: true
  },
  additions: {
    type: Number,
    default: 0
  },
  deletions: {
    type: Number,
    default: 0
  },
  options: {
    type: Object,
    default: () => ({})
  }
})

const diffContainer = ref(null)
let diffEditor = null

const defaultOptions = {
  automaticLayout: true,
  fontSize: 14,
  renderSideBySide: true,
  ignoreTrimWhitespace: false,
  renderIndicators: true,
  originalEditable: false,
  readOnly: true,
  minimap: { enabled: false },
  wordWrap: 'on',
  scrollBeyondLastLine: false
}

const initDiffEditor = () => {
  if (!diffContainer.value) return

  const options = {
    ...defaultOptions,
    ...props.options
  }

  diffEditor = monaco.editor.createDiffEditor(diffContainer.value, options)

  // 创建模型
  const originalModel = monaco.editor.createModel(props.originalCode, props.language)
  const modifiedModel = monaco.editor.createModel(props.modifiedCode, props.language)

  diffEditor.setModel({
    original: originalModel,
    modified: modifiedModel
  })
}

// 监听代码变化
watch([() => props.originalCode, () => props.modifiedCode], ([newOriginal, newModified]) => {
  if (diffEditor) {
    const model = diffEditor.getModel()
    if (model) {
      model.original.setValue(newOriginal || '')
      model.modified.setValue(newModified || '')
    }
  }
})

watch(() => props.language, (newLanguage) => {
  if (diffEditor) {
    const model = diffEditor.getModel()
    if (model) {
      monaco.editor.setModelLanguage(model.original, newLanguage)
      monaco.editor.setModelLanguage(model.modified, newLanguage)
    }
  }
})

onMounted(() => {
  nextTick(() => {
    initDiffEditor()
  })
})

onBeforeUnmount(() => {
  if (diffEditor) {
    diffEditor.dispose()
  }
})

defineExpose({
  getDiffEditor: () => diffEditor
})
</script>

<style lang="scss" scoped>
.diff-editor-container {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
  
  .diff-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: #f5f7fa;
    border-bottom: 1px solid #e4e7ed;
    font-size: 13px;
    
    .file-info {
      display: flex;
      align-items: center;
      gap: 6px;
      
      .file-path {
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        color: #606266;
      }
    }
    
    .diff-stats {
      display: flex;
      gap: 8px;
      
      .additions {
        color: #67c23a;
        font-weight: 500;
      }
      
      .deletions {
        color: #f56c6c;
        font-weight: 500;
      }
    }
  }
  
  .monaco-diff-editor {
    width: 100%;
  }
}
</style>