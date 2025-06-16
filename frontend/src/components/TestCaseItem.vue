<template>
  <el-card class="test-case-item" shadow="hover">
    <div class="test-header" @click="$emit('toggle-expanded')">
      <div class="test-main-info">
        <el-icon :class="expanded ? 'icon-expanded' : ''"><ArrowRight /></el-icon>
        <span class="test-name">{{ testCase.name }}</span>
        <el-tag size="small" :type="getTestTypeTag(testCase.type)" class="test-type">
          {{ getTestTypeLabel(testCase.type) }}
        </el-tag>
        <el-tag size="small" :type="getTestStatusTag(testCase.status)" class="test-status">
          {{ getTestStatusLabel(testCase.status) }}
        </el-tag>
      </div>
      
      <div class="test-actions">
        <el-tooltip content="Copy test code" placement="top">
          <el-button 
            type="primary" 
            size="small" 
            plain 
            circle 
            @click.stop="$emit('copy-code', testCase.code)"
          >
            <el-icon><DocumentCopy /></el-icon>
          </el-button>
        </el-tooltip>
        
        <el-tooltip content="Run test" placement="top">
          <el-button 
            type="success" 
            size="small" 
            plain 
            circle 
            @click.stop="$emit('run-test', testCase.id)"
          >
            <el-icon><VideoPlay /></el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </div>
    
    <div v-if="expanded" class="test-details">
      <div v-if="testCase.file_path" class="test-file-path">
        <strong>File:</strong> {{ testCase.file_path }}
      </div>
      
      <div v-if="testCase.description" class="test-description">
        <strong>Description:</strong> {{ testCase.description }}
      </div>
      
      <div v-if="testCase.generated_at" class="test-timestamp">
        <strong>Generated:</strong> {{ formatDate(testCase.generated_at) }}
      </div>
      
      <div class="test-code-container">
        <div class="code-header">
          <span>Test Code:</span>
          <el-tooltip content="Copy to clipboard" placement="top">
            <el-button 
              size="small" 
              text 
              @click="$emit('copy-code', testCase.code)"
            >
              <el-icon><DocumentCopy /></el-icon> Copy
            </el-button>
          </el-tooltip>
        </div>
        
        <code-editor 
          :model-value="testCase.code"
          :read-only="true"
          :language="getLanguageForTest(testCase.type)"
          :hide-footer="true"
        />
      </div>
    </div>
  </el-card>
</template>

<script>
import { defineComponent } from 'vue'
import { formatDate } from '@/utils/formatters'
import CodeEditor from './CodeEditor.vue'

export default defineComponent({
  name: 'TestCaseItem',
  components: { CodeEditor },
  
  props: {
    testCase: {
      type: Object,
      required: true
    },
    expanded: {
      type: Boolean,
      default: false
    }
  },
  
  emits: ['toggle-expanded', 'copy-code', 'run-test'],
  
  setup() {
    // Helper functions for test type display
    const getTestTypeTag = (type) => {
      const types = {
        'unit': 'info',
        'integration': 'warning',
        'e2e': 'success'
      }
      return types[type] || 'info'
    }
    
    const getTestTypeLabel = (type) => {
      const types = {
        'unit': 'Unit',
        'integration': 'Integration',
        'e2e': 'E2E'
      }
      return types[type] || type
    }
    
    // Helper functions for test status display
    const getTestStatusTag = (status) => {
      const statuses = {
        'passed': 'success',
        'failed': 'danger',
        'skipped': 'info',
        'not_run': ''
      }
      return statuses[status] || ''
    }
    
    const getTestStatusLabel = (status) => {
      const statuses = {
        'passed': 'Passed',
        'failed': 'Failed',
        'skipped': 'Skipped',
        'not_run': 'Not Run'
      }
      return statuses[status] || status
    }
    
    // Get language for code editor based on test type
    const getLanguageForTest = (type) => {
      const languages = {
        'unit': 'javascript',
        'integration': 'javascript',
        'e2e': 'javascript'
      }
      return languages[type] || 'javascript'
    }
    
    return {
      formatDate,
      getTestTypeTag,
      getTestTypeLabel,
      getTestStatusTag,
      getTestStatusLabel,
      getLanguageForTest
    }
  }
})
</script>

<style scoped>
.test-case-item {
  transition: all 0.2s ease;
}

.test-case-item:hover {
  transform: translateY(-2px);
}

.test-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  padding: 0.5rem 0;
}

.test-main-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  overflow: hidden;
}

.icon-expanded {
  transform: rotate(90deg);
}

.test-name {
  font-weight: 500;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.test-type, .test-status {
  flex-shrink: 0;
}

.test-actions {
  display: flex;
  gap: 0.5rem;
}

.test-details {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.test-description, .test-file-path, .test-timestamp {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.test-code-container {
  margin-top: 0.5rem;
}

.code-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
  color: var(--text-secondary);
}
</style> 