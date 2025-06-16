<template>
  <div class="diff-viewer-container">
    <div class="diff-header" v-if="!hideHeader">
      <div class="diff-file-path">
        <el-tag size="small" :type="getChangeType(file)">{{ getChangeTypeLabel(file) }}</el-tag>
        <span class="file-path">{{ file.path }}</span>
      </div>
      <div class="diff-stats">
        <span class="additions">+{{ file.additions || 0 }}</span>
        <span class="deletions">-{{ file.deletions || 0 }}</span>
      </div>
    </div>
    
    <div v-if="renderAs === 'monaco'">
      <CodeEditor
        :diff="true"
        :original="originalContent"
        :modified="modifiedContent"
        :language="language"
        :read-only="true"
        :file-path="file.path"
        :diff-options="diffOptions"
        :hide-footer="true"
        @editor-mounted="handleEditorMounted"
      />
    </div>
    
    <div v-else-if="renderAs === 'html'" class="diff-html-container" v-html="diffHtml"></div>
    
    <div v-else class="diff-plain-container">
      <pre><code class="diff-code" :class="{ 'dark-mode': isDarkMode }">{{ plainDiff }}</code></pre>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { useStore } from 'vuex'
import * as Diff2Html from 'diff2html'
import CodeEditor from './CodeEditor.vue'
import { getLanguageFromFilename } from '@/utils/formatters'

export default {
  name: 'DiffViewer',
  components: { CodeEditor },
  
  props: {
    file: {
      type: Object,
      required: true,
      default: () => ({
        path: '',
        content: '',
        originalContent: '',
        additions: 0,
        deletions: 0,
        changeType: 'modified'
      })
    },
    renderAs: {
      type: String,
      default: 'monaco',
      validator: (value) => ['monaco', 'html', 'plain'].includes(value)
    },
    diffOptions: {
      type: Object,
      default: () => ({})
    },
    hideHeader: {
      type: Boolean,
      default: false
    }
  },
  
  setup(props) {
    const store = useStore()
    const isDarkMode = computed(() => store.getters.isDarkMode)
    const diffHtml = ref('')
    const plainDiff = ref('')
    const monacoEditor = ref(null)
    
    // Get language for syntax highlighting based on file extension
    const language = computed(() => {
      return getLanguageFromFilename(props.file.path)
    })
    
    // Get content for diff viewer
    const originalContent = computed(() => {
      return props.file.originalContent || ''
    })
    
    const modifiedContent = computed(() => {
      return props.file.content || ''
    })
    
    // Functions to determine change type
    const getChangeType = (file) => {
      if (file.changeType === 'added') return 'success'
      if (file.changeType === 'deleted') return 'danger'
      if (file.changeType === 'renamed') return 'info'
      return 'warning' // modified
    }
    
    const getChangeTypeLabel = (file) => {
      if (file.changeType === 'added') return 'Added'
      if (file.changeType === 'deleted') return 'Deleted'
      if (file.changeType === 'renamed') return 'Renamed'
      return 'Modified'
    }
    
    // Generate diff HTML for display
    const generateDiffHtml = () => {
      let diffText = ''
      
      // Create unified diff format
      if (props.file.changeType === 'added') {
        diffText = `--- /dev/null\n+++ b/${props.file.path}\n@@ -0,0 +1,${modifiedContent.value.split('\n').length} @@\n`
        modifiedContent.value.split('\n').forEach(line => {
          diffText += `+${line}\n`
        })
      } else if (props.file.changeType === 'deleted') {
        diffText = `--- a/${props.file.path}\n+++ /dev/null\n@@ -1,${originalContent.value.split('\n').length} +0,0 @@\n`
        originalContent.value.split('\n').forEach(line => {
          diffText += `-${line}\n`
        })
      } else {
        // Use actual diff if provided, or generate one
        if (props.file.diff) {
          diffText = props.file.diff
        } else {
          // Simple line by line diff
          const originalLines = originalContent.value.split('\n')
          const modifiedLines = modifiedContent.value.split('\n')
          
          diffText = `--- a/${props.file.path}\n+++ b/${props.file.path}\n`
          
          // Very simplified diff - in a real app you'd use a proper diffing library
          // This is just for demonstration
          let lineNum = 1
          const maxLines = Math.max(originalLines.length, modifiedLines.length)
          
          for (let i = 0; i < maxLines; i++) {
            const originalLine = originalLines[i] || ''
            const modifiedLine = modifiedLines[i] || ''
            
            if (originalLine !== modifiedLine) {
              if (originalLine) {
                diffText += `-${originalLine}\n`
              }
              if (modifiedLine) {
                diffText += `+${modifiedLine}\n`
              }
            } else {
              diffText += ` ${originalLine}\n`
            }
            lineNum++
          }
        }
      }
      
      plainDiff.value = diffText
      
      // Generate HTML diff
      if (props.renderAs === 'html') {
        const diffJson = Diff2Html.parse(diffText)
        diffHtml.value = Diff2Html.html(diffJson, {
          drawFileList: false,
          matching: 'lines',
          outputFormat: 'side-by-side',
          ...props.diffOptions
        })
      }
    }
    
    // Handle monaco editor mount
    const handleEditorMounted = (editor) => {
      monacoEditor.value = editor
    }
    
    // Generate diff when component mounts
    onMounted(() => {
      generateDiffHtml()
    })
    
    // Regenerate diff when props change
    watch(() => props.file, () => {
      generateDiffHtml()
    }, { deep: true })
    
    watch(() => props.renderAs, () => {
      generateDiffHtml()
    })
    
    return {
      diffHtml,
      plainDiff,
      originalContent,
      modifiedContent,
      language,
      isDarkMode,
      getChangeType,
      getChangeTypeLabel,
      handleEditorMounted
    }
  }
}
</script>

<style scoped>
.diff-viewer-container {
  margin-bottom: 1.5rem;
}

.diff-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background-color: var(--background-color);
  border: 1px solid var(--border-color);
  border-bottom: none;
  border-radius: 8px 8px 0 0;
}

.diff-file-path {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  overflow: hidden;
}

.file-path {
  font-family: monospace;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.diff-stats {
  display: flex;
  gap: 0.5rem;
  font-family: monospace;
  font-size: 0.9rem;
}

.additions {
  color: var(--success-color);
}

.deletions {
  color: var(--danger-color);
}

.diff-plain-container {
  border: 1px solid var(--border-color);
  border-radius: 0 0 8px 8px;
  overflow: auto;
  max-height: 500px;
}

.diff-html-container {
  border: 1px solid var(--border-color);
  border-radius: 0 0 8px 8px;
  overflow: auto;
  max-height: 500px;
}

.diff-code {
  margin: 0;
  padding: 1rem;
  font-family: monospace;
  font-size: 0.9rem;
  line-height: 1.5;
  white-space: pre;
  color: var(--text-regular);
  background-color: #fafafa;
}

.diff-code.dark-mode {
  background-color: #1e1e1e;
  color: #d4d4d4;
}

:deep(.d2h-file-header) {
  display: none;
}

:deep(.d2h-file-wrapper) {
  border: none;
  margin-bottom: 0;
}

:deep(.d2h-file-diff) {
  overflow-x: auto;
}
</style> 