<template>
  <div class="test-case-viewer">
    <el-tabs v-model="activeTab" type="card">
      <el-tab-pane label="All Tests" name="all">
        <test-case-filters
          v-model:search="searchQuery"
          v-model:type="selectedType"
          v-model:status="selectedStatus"
          :test-types="testTypes"
          :test-statuses="testStatuses"
        />
        
        <div class="test-cases-list">
          <template v-if="filteredTestCases.length > 0">
            <test-case-item 
              v-for="testCase in filteredTestCases" 
              :key="testCase.id" 
              :test-case="testCase"
              :expanded="expandedTests.includes(testCase.id)"
              @toggle-expanded="toggleExpandTest(testCase.id)"
              @copy-code="copyTestCode"
              @run-test="runTest"
            />
          </template>
          <el-empty v-else description="No test cases found" />
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="Unit Tests" name="unit">
        <test-case-filters
          v-model:search="searchQuery"
          v-model:status="selectedStatus"
          :test-statuses="testStatuses"
        />
        
        <div class="test-cases-list">
          <template v-if="unitTests.length > 0">
            <test-case-item 
              v-for="testCase in unitTests" 
              :key="testCase.id" 
              :test-case="testCase"
              :expanded="expandedTests.includes(testCase.id)"
              @toggle-expanded="toggleExpandTest(testCase.id)"
              @copy-code="copyTestCode"
              @run-test="runTest"
            />
          </template>
          <el-empty v-else description="No unit tests found" />
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="Integration Tests" name="integration">
        <test-case-filters
          v-model:search="searchQuery"
          v-model:status="selectedStatus"
          :test-statuses="testStatuses"
        />
        
        <div class="test-cases-list">
          <template v-if="integrationTests.length > 0">
            <test-case-item 
              v-for="testCase in integrationTests" 
              :key="testCase.id" 
              :test-case="testCase"
              :expanded="expandedTests.includes(testCase.id)"
              @toggle-expanded="toggleExpandTest(testCase.id)"
              @copy-code="copyTestCode"
              @run-test="runTest"
            />
          </template>
          <el-empty v-else description="No integration tests found" />
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="E2E Tests" name="e2e">
        <test-case-filters
          v-model:search="searchQuery"
          v-model:status="selectedStatus"
          :test-statuses="testStatuses"
        />
        
        <div class="test-cases-list">
          <template v-if="e2eTests.length > 0">
            <test-case-item 
              v-for="testCase in e2eTests" 
              :key="testCase.id" 
              :test-case="testCase"
              :expanded="expandedTests.includes(testCase.id)"
              @toggle-expanded="toggleExpandTest(testCase.id)"
              @copy-code="copyTestCode"
              @run-test="runTest"
            />
          </template>
          <el-empty v-else description="No E2E tests found" />
        </div>
      </el-tab-pane>
    </el-tabs>
    
    <div class="actions-bar">
      <el-button type="primary" @click="exportTestCases" :loading="exporting">
        <el-icon><Download /></el-icon> Export Tests
      </el-button>
    </div>
  </div>
</template>

<script>
import { ref, computed, defineComponent } from 'vue'
import { useStore } from 'vuex'
import { ElMessage } from 'element-plus'
import TestCaseItem from './TestCaseItem.vue'
import TestCaseFilters from './TestCaseFilters.vue'
import { exportTestCases as exportTestCasesApi } from '@/api/analysis'

export default defineComponent({
  name: 'TestCaseViewer',
  
  components: {
    TestCaseItem,
    TestCaseFilters
  },
  
  props: {
    testCases: {
      type: Array,
      required: true,
      default: () => []
    },
    projectId: {
      type: [Number, String],
      required: true
    }
  },
  
  setup(props) {
    const store = useStore()
    const activeTab = ref('all')
    const searchQuery = ref('')
    const selectedType = ref('')
    const selectedStatus = ref('')
    const expandedTests = ref([])
    const exporting = ref(false)
    
    // Test types and statuses for filters
    const testTypes = [
      { label: 'All Types', value: '' },
      { label: 'Unit Tests', value: 'unit' },
      { label: 'Integration Tests', value: 'integration' },
      { label: 'E2E Tests', value: 'e2e' }
    ]
    
    const testStatuses = [
      { label: 'All Statuses', value: '' },
      { label: 'Passed', value: 'passed' },
      { label: 'Failed', value: 'failed' },
      { label: 'Skipped', value: 'skipped' },
      { label: 'Not Run', value: 'not_run' }
    ]
    
    // Filtered test cases based on search and filters
    const filteredTestCases = computed(() => {
      return props.testCases.filter(test => {
        // Filter by type if selected
        if (selectedType.value && test.type !== selectedType.value) {
          return false
        }
        
        // Filter by status if selected
        if (selectedStatus.value && test.status !== selectedStatus.value) {
          return false
        }
        
        // Filter by search query
        if (searchQuery.value) {
          const query = searchQuery.value.toLowerCase()
          return (
            test.name.toLowerCase().includes(query) ||
            test.description?.toLowerCase().includes(query) ||
            test.file_path?.toLowerCase().includes(query)
          )
        }
        
        return true
      })
    })
    
    // Test cases filtered by type
    const unitTests = computed(() => {
      return filteredByTypeAndSearch('unit')
    })
    
    const integrationTests = computed(() => {
      return filteredByTypeAndSearch('integration')
    })
    
    const e2eTests = computed(() => {
      return filteredByTypeAndSearch('e2e')
    })
    
    // Helper function for filtering by type and search
    const filteredByTypeAndSearch = (type) => {
      return props.testCases.filter(test => {
        // Filter by type
        if (test.type !== type) {
          return false
        }
        
        // Filter by status if selected
        if (selectedStatus.value && test.status !== selectedStatus.value) {
          return false
        }
        
        // Filter by search query
        if (searchQuery.value) {
          const query = searchQuery.value.toLowerCase()
          return (
            test.name.toLowerCase().includes(query) ||
            test.description?.toLowerCase().includes(query) ||
            test.file_path?.toLowerCase().includes(query)
          )
        }
        
        return true
      })
    }
    
    // Toggle the expanded state of a test
    const toggleExpandTest = (testId) => {
      const index = expandedTests.value.indexOf(testId)
      if (index === -1) {
        expandedTests.value.push(testId)
      } else {
        expandedTests.value.splice(index, 1)
      }
    }
    
    // Copy test code to clipboard
    const copyTestCode = (code) => {
      navigator.clipboard.writeText(code).then(() => {
        ElMessage({
          message: 'Test code copied to clipboard',
          type: 'success',
          duration: 2000
        })
      }).catch(err => {
        console.error('Failed to copy code:', err)
        ElMessage({
          message: 'Failed to copy code',
          type: 'error'
        })
      })
    }
    
    // Run a specific test
    const runTest = (testId) => {
      ElMessage({
        message: 'Running test is not implemented in this demo',
        type: 'info'
      })
    }
    
    // Export test cases
    const exportTestCases = async () => {
      exporting.value = true
      try {
        const format = 'json' // Could be a user selection
        const response = await exportTestCasesApi(props.projectId, format)
        
        // Create a download link
        const url = window.URL.createObjectURL(new Blob([response]))
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', `tests-${props.projectId}.${format}`)
        document.body.appendChild(link)
        link.click()
        link.remove()
        
        ElMessage({
          message: 'Tests exported successfully',
          type: 'success'
        })
      } catch (error) {
        console.error('Failed to export test cases:', error)
        ElMessage({
          message: 'Failed to export test cases',
          type: 'error'
        })
      } finally {
        exporting.value = false
      }
    }
    
    return {
      activeTab,
      searchQuery,
      selectedType,
      selectedStatus,
      expandedTests,
      exporting,
      testTypes,
      testStatuses,
      filteredTestCases,
      unitTests,
      integrationTests,
      e2eTests,
      toggleExpandTest,
      copyTestCode,
      runTest,
      exportTestCases
    }
  }
})
</script>

<style scoped>
.test-case-viewer {
  margin-bottom: 2rem;
}

.test-cases-list {
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.actions-bar {
  margin-top: 1.5rem;
  display: flex;
  justify-content: flex-end;
}

:deep(.el-tabs__header) {
  margin-bottom: 1.5rem;
}

:deep(.el-tabs__item) {
  height: 40px;
  line-height: 40px;
}

:deep(.el-tabs__item.is-active) {
  font-weight: 600;
}
</style> 