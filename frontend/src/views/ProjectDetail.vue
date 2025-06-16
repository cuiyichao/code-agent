<template>
  <div class="project-detail-view">
    <!-- Loading State -->
    <div v-if="loading">
      <el-skeleton :rows="10" animated />
    </div>
    
    <!-- Error State -->
    <el-alert v-if="error" :title="error" type="error" show-icon class="mb-4" />
    
    <!-- Project Content -->
    <template v-if="!loading && !error && project">
      <!-- Header -->
      <el-row :gutter="20" class="mb-4">
        <el-col :md="16">
          <div class="d-flex align-center">
            <h1 class="page-title">{{ project.name }}</h1>
            <el-tag class="ml-3" :type="getRiskLevelTag(project.risk_level)" size="large">
              {{ getRiskLevelText(project.risk_level) }}
            </el-tag>
          </div>
          <p class="project-git-url">
            <el-icon><Link /></el-icon>
            <a :href="project.git_url" target="_blank" rel="noopener">{{ project.git_url }}</a>
            <span class="branch-label">
              Branch: <strong>{{ project.branch || 'main' }}</strong>
            </span>
          </p>
        </el-col>
        
        <el-col :md="8" class="text-right">
          <el-button-group>
            <el-button type="primary" @click="navigateToAnalysis">
              <el-icon><DataAnalysis /></el-icon> View Analysis
            </el-button>
            <el-button @click="startNewAnalysis" :loading="analyzing">
              <el-icon><RefreshRight /></el-icon> New Analysis
            </el-button>
          </el-button-group>
        </el-col>
      </el-row>
      
      <!-- Project Stats Cards -->
      <el-row :gutter="20" class="mb-4">
        <el-col :xs="24" :sm="12" :md="6">
          <el-card shadow="hover" class="stat-card">
            <template #header>
              <div class="stat-header">
                <span>Files</span>
                <el-icon><Document /></el-icon>
              </div>
            </template>
            <div class="stat-value">{{ project.stats?.files_count || 0 }}</div>
          </el-card>
        </el-col>
        
        <el-col :xs="24" :sm="12" :md="6">
          <el-card shadow="hover" class="stat-card">
            <template #header>
              <div class="stat-header">
                <span>Changes</span>
                <el-icon><Edit /></el-icon>
              </div>
            </template>
            <div class="stat-value">{{ project.stats?.changes_count || 0 }}</div>
          </el-card>
        </el-col>
        
        <el-col :xs="24" :sm="12" :md="6">
          <el-card shadow="hover" class="stat-card">
            <template #header>
              <div class="stat-header">
                <span>Tests</span>
                <el-icon><Check /></el-icon>
              </div>
            </template>
            <div class="stat-value">{{ project.stats?.tests_count || 0 }}</div>
          </el-card>
        </el-col>
        
        <el-col :xs="24" :sm="12" :md="6">
          <el-card shadow="hover" class="stat-card">
            <template #header>
              <div class="stat-header">
                <span>Risk Score</span>
                <el-icon><Warning /></el-icon>
              </div>
            </template>
            <div class="stat-value" :style="{color: getRiskLevelColor(project.risk_level)}">
              {{ project.risk_score || 0 }}
            </div>
          </el-card>
        </el-col>
      </el-row>
      
      <!-- Project Tabs -->
      <el-tabs v-model="activeTab" class="project-tabs">
        <el-tab-pane label="Overview" name="overview">
          <overview-tab :project="project" />
        </el-tab-pane>
        
        <el-tab-pane label="Test Cases" name="tests">
          <test-case-viewer 
            :test-cases="testCases" 
            :project-id="project.id" 
          />
        </el-tab-pane>
        
        <el-tab-pane label="Code Changes" name="changes">
          <changes-tab :project="project" />
        </el-tab-pane>
        
        <el-tab-pane label="Settings" name="settings">
          <settings-tab 
            :project="project" 
            @project-updated="fetchProjectDetails"
            @project-deleted="handleProjectDeleted"
          />
        </el-tab-pane>
      </el-tabs>
    </template>
    
    <!-- Not Found State -->
    <el-empty v-if="!loading && !project && !error" description="Project not found">
      <router-link to="/">
        <el-button type="primary">Back to Projects</el-button>
      </router-link>
    </el-empty>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStore } from 'vuex'
import { ElMessage, ElMessageBox } from 'element-plus'
import TestCaseViewer from '@/components/TestCaseViewer.vue'
import { formatRiskLevel } from '@/utils/formatters'

// These would be actual components in a real implementation
const OverviewTab = defineComponent({
  name: 'OverviewTab',
  props: ['project'],
  template: '<div>Overview tab content would go here</div>'
})

const ChangesTab = defineComponent({
  name: 'ChangesTab',
  props: ['project'],
  template: '<div>Changes tab content would go here</div>'
})

const SettingsTab = defineComponent({
  name: 'SettingsTab',
  props: ['project'],
  emits: ['project-updated', 'project-deleted'],
  template: '<div>Settings tab content would go here</div>'
})

import { defineComponent } from 'vue'

export default defineComponent({
  name: 'ProjectDetail',
  
  components: {
    TestCaseViewer,
    OverviewTab,
    ChangesTab,
    SettingsTab
  },
  
  setup() {
    const store = useStore()
    const route = useRoute()
    const router = useRouter()
    
    const projectId = computed(() => route.params.id)
    const activeTab = ref('overview')
    const analyzing = ref(false)
    
    const project = computed(() => store.getters['projects/getProjectById'](projectId.value))
    const loading = computed(() => store.state.projects.loading)
    const error = computed(() => store.state.projects.error)
    
    const testCases = computed(() => {
      return store.getters['analysis/getTestCasesByProjectId'](projectId.value) || []
    })
    
    // Fetch project details
    const fetchProjectDetails = async () => {
      try {
        await store.dispatch('projects/fetchProjectById', projectId.value)
        await store.dispatch('analysis/fetchTestCases', projectId.value)
      } catch (err) {
        // Error handling is done in the store
      }
    }
    
    // Navigate to analysis page
    const navigateToAnalysis = () => {
      router.push({ name: 'ProjectAnalysis', params: { id: projectId.value } })
    }
    
    // Start a new analysis
    const startNewAnalysis = async () => {
      try {
        analyzing.value = true
        await store.dispatch('projects/analyzeProject', projectId.value)
        ElMessage.success('Analysis started successfully')
        navigateToAnalysis()
      } catch (err) {
        ElMessage.error(err.message || 'Failed to start analysis')
      } finally {
        analyzing.value = false
      }
    }
    
    // Handle project deletion
    const handleProjectDeleted = () => {
      ElMessage.success('Project deleted successfully')
      router.push('/')
    }
    
    // Get risk level tag, text and color
    const getRiskLevelTag = (level) => {
      const levels = {
        0: 'success',
        1: 'info',
        2: 'warning',
        3: 'danger'
      }
      return levels[level] || 'info'
    }
    
    const getRiskLevelText = (level) => {
      const levels = {
        0: 'No Risk',
        1: 'Low',
        2: 'Medium',
        3: 'High'
      }
      return levels[level] || 'Unknown'
    }
    
    const getRiskLevelColor = (level) => {
      return formatRiskLevel(level).color
    }
    
    // Fetch data on mount
    onMounted(fetchProjectDetails)
    
    return {
      project,
      loading,
      error,
      testCases,
      activeTab,
      analyzing,
      navigateToAnalysis,
      startNewAnalysis,
      handleProjectDeleted,
      fetchProjectDetails,
      getRiskLevelTag,
      getRiskLevelText,
      getRiskLevelColor
    }
  }
})
</script>

<style scoped>
.project-detail-view {
  max-width: 100%;
  margin: 0 auto;
}

.project-git-url {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-secondary);
  margin-top: 0.5rem;
}

.project-git-url a {
  color: var(--text-regular);
  text-decoration: none;
}

.project-git-url a:hover {
  text-decoration: underline;
}

.branch-label {
  margin-left: 1.5rem;
  display: inline-flex;
  align-items: center;
}

.text-right {
  display: flex;
  justify-content: flex-end;
}

.stat-card {
  height: 100%;
  transition: transform 0.2s;
}

.stat-card:hover {
  transform: translateY(-5px);
}

.stat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-value {
  font-size: 2rem;
  font-weight: 600;
  text-align: center;
  padding: 1rem 0;
  color: var(--text-primary);
}

.project-tabs {
  margin-top: 2rem;
}

:deep(.el-tabs__header) {
  margin-bottom: 1.5rem;
}

:deep(.el-tabs__item) {
  height: 3rem;
  line-height: 3rem;
  font-weight: 500;
}
</style>