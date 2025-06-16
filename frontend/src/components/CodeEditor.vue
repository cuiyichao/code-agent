<template>
  <div class="code-editor-container" :class="{ 'fullscreen': isFullScreen }">
    <div class="editor-toolbar">
      <span class="file-path" v-if="filePath">{{ filePath }}</span>
      <div class="toolbar-actions">
        <el-dropdown v-if="languages.length > 1" trigger="click" @command="changeLanguage">
          <el-button size="small" type="info" plain>
            {{ currentLanguage }}
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item 
                v-for="lang in languages" 
                :key="lang.value" 
                :command="lang.value"
              >
                {{ lang.label }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        
        <el-button 
          size="small" 
          :type="readOnly ? 'info' : 'warning'" 
          plain 
          @click="toggleReadOnly" 
          :icon="readOnly ? 'Lock' : 'Edit'"
        >
          {{ readOnly ? 'Read Only' : 'Editable' }}
        </el-button>
        
        <el-button 
          size="small" 
          :type="theme === 'vs-dark' ? 'primary' : 'default'" 
          plain 
          @click="toggleTheme" 
          :icon="theme === 'vs-dark' ? 'Sunny' : 'Moon'"
        >
          {{ theme === 'vs-dark' ? 'Light Theme' : 'Dark Theme' }}
        </el-button>
        
        <el-button 
          size="small" 
          type="success" 
          plain 
          @click="toggleFullScreen" 
          :icon="isFullScreen ? 'SwitchButton' : 'FullScreen'"
        >
          {{ isFullScreen ? 'Exit Fullscreen' : 'Fullscreen' }}
        </el-button>
      </div>
    </div>
    
    <div ref="monacoContainer" class="monaco-container"></div>
    
    <div class="editor-footer" v-if="!hideFooter">
      <div class="editor-stats">
        {{ currentStats }}
      </div>
      <div class="editor-actions">
        <el-button 
          v-if="!readOnly" 
          size="small" 
          type="primary" 
          @click="$emit('save', getCode())" 
          :disabled="!codeChanged"
        >
          Save Changes
        </el-button>
        <el-button 
          size="small" 
          @click="$emit('cancel')" 
          v-if="showCancelButton"
        >
          Cancel
        </el-button>
        <slot name="footer-actions"></slot>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import * as monaco from 'monaco-editor'
import { useStore } from 'vuex'

export default {
  name: 'CodeEditor',
  
  props: {
    modelValue: {
      type: String,
      default: ''
    },
    language: {
      type: String,
      default: 'javascript'
    },
    readOnly: {
      type: Boolean,
      default: false
    },
    filePath: {
      type: String,
      default: ''
    },
    diff: {
      type: Boolean,
      default: false
    },
    original: {
      type: String,
      default: ''
    },
    modified: {
      type: String,
      default: ''
    },
    diffOptions: {
      type: Object,
      default: () => ({})
    },
    hideFooter: {
      type: Boolean,
      default: false
    },
    showCancelButton: {
      type: Boolean,
      default: false
    },
    editorOptions: {
      type: Object,
      default: () => ({})
    }
  },
  
  emits: ['update:modelValue', 'save', 'cancel', 'editor-mounted'],
  
  setup(props, { emit }) {
    const monacoContainer = ref(null)
    const editor = ref(null)
    const isFullScreen = ref(false)
    const codeChanged = ref(false)
    const store = useStore()
    let diffEditor = null
    
    // Use store dark mode setting for initial theme
    const isDarkMode = computed(() => store.getters.isDarkMode)
    const theme = ref(isDarkMode.value ? 'vs-dark' : 'vs')
    
    // Languages available in the dropdown
    const languages = [
      { label: 'JavaScript', value: 'javascript' },
      { label: 'TypeScript', value: 'typescript' },
      { label: 'HTML', value: 'html' },
      { label: 'CSS', value: 'css' },
      { label: 'Python', value: 'python' },
      { label: 'Java', value: 'java' },
      { label: 'Go', value: 'go' },
      { label: 'C++', value: 'cpp' },
      { label: 'JSON', value: 'json' },
      { label: 'Markdown', value: 'markdown' }
    ]
    
    const currentLanguage = computed(() => {
      const lang = languages.find(l => l.value === props.language)
      return lang ? lang.label : 'Plain Text'
    })
    
    const currentStats = computed(() => {
      if (!editor.value) return ''
      
      const position = editor.value.getPosition()
      const model = editor.value.getModel()
      
      if (!position || !model) return ''
      
      const lineCount = model.getLineCount()
      return `Line ${position.lineNumber}:${position.column} | ${lineCount} lines`
    })
    
    // Initialize editor
    const initMonacoEditor = () => {
      if (props.diff) {
        initDiffEditor()
      } else {
        initNormalEditor()
      }
    }
    
    // Initialize normal editor
    const initNormalEditor = () => {
      const defaultOptions = {
        value: props.modelValue,
        language: props.language,
        theme: theme.value,
        automaticLayout: true,
        readOnly: props.readOnly,
        minimap: { enabled: true },
        scrollBeyondLastLine: false,
        fontSize: 14,
        lineNumbers: 'on',
        folding: true,
        formatOnPaste: true,
        tabSize: 2
      }
      
      editor.value = monaco.editor.create(monacoContainer.value, {
        ...defaultOptions,
        ...props.editorOptions
      })
      
      // Set up event listeners
      editor.value.onDidChangeModelContent(() => {
        const value = editor.value.getValue()
        emit('update:modelValue', value)
        codeChanged.value = value !== props.modelValue
      })
      
      // Emit editor instance for parent components to use
      emit('editor-mounted', editor.value)
    }
    
    // Initialize diff editor
    const initDiffEditor = () => {
      const defaultOptions = {
        originalEditable: false,
        readOnly: props.readOnly,
        theme: theme.value,
        automaticLayout: true,
        renderSideBySide: true,
        fontSize: 14,
        lineNumbers: 'on'
      }
      
      diffEditor = monaco.editor.createDiffEditor(monacoContainer.value, {
        ...defaultOptions,
        ...props.diffOptions
      })
      
      const originalModel = monaco.editor.createModel(
        props.original,
        props.language
      )
      
      const modifiedModel = monaco.editor.createModel(
        props.modified,
        props.language
      )
      
      diffEditor.setModel({
        original: originalModel,
        modified: modifiedModel
      })
      
      editor.value = diffEditor.getModifiedEditor()
      
      // Set up event listeners
      editor.value.onDidChangeModelContent(() => {
        const value = editor.value.getValue()
        emit('update:modelValue', value)
        codeChanged.value = value !== props.modified
      })
      
      // Emit editor instance for parent components to use
      emit('editor-mounted', editor.value)
    }
    
    // Toggle theme
    const toggleTheme = () => {
      theme.value = theme.value === 'vs' ? 'vs-dark' : 'vs'
      monaco.editor.setTheme(theme.value)
    }
    
    // Toggle read only
    const toggleReadOnly = () => {
      const newReadOnly = !editor.value.getOption(monaco.editor.EditorOption.readOnly)
      editor.value.updateOptions({ readOnly: newReadOnly })
      
      if (diffEditor) {
        diffEditor.updateOptions({ readOnly: newReadOnly })
      }
    }
    
    // Toggle full screen
    const toggleFullScreen = () => {
      isFullScreen.value = !isFullScreen.value
      
      // Force layout update when toggling fullscreen
      setTimeout(() => {
        editor.value.layout()
      }, 100)
    }
    
    // Change language
    const changeLanguage = (language) => {
      const model = editor.value.getModel()
      monaco.editor.setModelLanguage(model, language)
    }
    
    // Get current code
    const getCode = () => {
      if (!editor.value) return props.modelValue
      return editor.value.getValue()
    }
    
    // Watch for external changes to modelValue
    watch(() => props.modelValue, (newValue) => {
      if (editor.value && newValue !== editor.value.getValue()) {
        editor.value.setValue(newValue)
        codeChanged.value = false
      }
    })
    
    // Watch for language changes
    watch(() => props.language, (newLanguage) => {
      if (editor.value) {
        const model = editor.value.getModel()
        monaco.editor.setModelLanguage(model, newLanguage)
      }
    })
    
    // Watch for readOnly changes
    watch(() => props.readOnly, (newValue) => {
      if (editor.value) {
        editor.value.updateOptions({ readOnly: newValue })
      }
    })
    
    // Watch for dark mode changes from store
    watch(() => isDarkMode.value, (newValue) => {
      theme.value = newValue ? 'vs-dark' : 'vs'
      monaco.editor.setTheme(theme.value)
    })
    
    // Mount and unmount
    onMounted(() => {
      initMonacoEditor()
      
      // Handle window resize
      window.addEventListener('resize', handleResize)
    })
    
    onBeforeUnmount(() => {
      if (editor.value) {
        editor.value.dispose()
      }
      
      if (diffEditor) {
        diffEditor.dispose()
      }
      
      window.removeEventListener('resize', handleResize)
    })
    
    // Resize handler
    const handleResize = () => {
      if (editor.value) {
        editor.value.layout()
      }
    }
    
    return {
      monacoContainer,
      editor,
      isFullScreen,
      theme,
      languages,
      currentLanguage,
      currentStats,
      codeChanged,
      toggleTheme,
      toggleReadOnly,
      toggleFullScreen,
      changeLanguage,
      getCode
    }
  }
}
</script>

<style scoped>
.code-editor-container {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 500px;
  transition: all 0.3s ease;
}

.code-editor-container.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  height: 100vh;
  width: 100vw;
  z-index: 9999;
  border-radius: 0;
  background-color: var(--background-color);
}

.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background-color: var(--background-color);
  border-bottom: 1px solid var(--border-color);
}

.file-path {
  font-family: monospace;
  font-size: 0.9rem;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.monaco-container {
  flex: 1;
  width: 100%;
  min-height: 200px;
}

.editor-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background-color: var(--background-color);
  border-top: 1px solid var(--border-color);
}

.editor-stats {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.editor-actions {
  display: flex;
  gap: 8px;
}
</style>