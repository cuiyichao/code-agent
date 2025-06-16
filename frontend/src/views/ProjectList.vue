<template>
  <div class="project-list-view">
    <el-row :gutter="20">
      <el-col :lg="24">
        <h1 class="page-title">Projects</h1>
        <p class="page-description">Manage and analyze your code repositories</p>
      </el-col>
    </el-row>

    <!-- Loading and Error States -->
    <el-row v-if="loading">
      <el-col :lg="24" class="loading-container">
        <el-skeleton :rows="6" animated />
      </el-col>
    </el-row>

    <el-alert v-if="error" :title="error" type="error" show-icon class="mb-4" />

    <!-- Project Grid -->
    <el-row v-if="!loading" :gutter="20">
      <el-col v-for="project in projects" :key="project.id" :xs="24" :sm="12" :md="8" :lg="6" class="mb-4">
        <ProjectCard :project="project" />
      </el-col>

      <!-- Empty State -->
      <el-col v-if="!loading && projects.length === 0" :lg="24">
        <el-empty description="No projects found">
          <router-link to="/new">
            <el-button type="primary">Create New Project</el-button>
          </router-link>
        </el-empty>
      </el-col>
    </el-row>

    <!-- Floating Action Button -->
    <router-link to="/new" class="create-button">
      <el-button type="primary" circle size="large">
        <el-icon><Plus /></el-icon>
      </el-button>
    </router-link>
  </div>
</template>

<script>
import { computed, onMounted } from 'vue'
import { useStore } from 'vuex'
import { useRouter } from 'vue-router'
import ProjectCard from '@/components/ProjectCard.vue'

export default {
  name: 'ProjectList',
  
  components: {
    ProjectCard
  },
  
  setup() {
    const store = useStore()
    const router = useRouter()
    
    // Get projects from store
    const projects = computed(() => store.state.projects.list)
    const loading = computed(() => store.state.projects.loading)
    const error = computed(() => store.state.projects.error)
    
    // Fetch projects on component mount
    onMounted(() => {
      store.dispatch('projects/fetchProjects')
    })
    
    return {
      projects,
      loading,
      error
    }
  }
}
</script>

<style scoped>
.project-list-view {
  position: relative;
  padding-bottom: 80px;
}

.page-title {
  font-size: 1.8rem;
  margin-bottom: 0.5rem;
}

.page-description {
  color: var(--el-text-color-secondary);
  margin-bottom: 2rem;
}

.mb-4 {
  margin-bottom: 16px;
}

.h-full {
  height: 100%;
}

.project-card {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.project-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.project-name {
  margin: 0;
  font-size: 1.2rem;
  flex: 1;
}

.project-meta {
  margin-bottom: 1rem;
}

.meta-item {
  display: flex;
  align-items: center;
  margin-bottom: 0.5rem;
  color: var(--el-text-color-secondary);
}

.meta-item i {
  margin-right: 0.5rem;
}

.git-url {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-stats {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1.5rem;
  margin-top: auto;
}

.stat-item {
  text-align: center;
  flex: 1;
}

.stat-label {
  display: block;
  font-size: 0.8rem;
  color: var(--el-text-color-secondary);
}

.stat-value {
  display: block;
  font-weight: bold;
  font-size: 1.2rem;
}

.project-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 1rem;
}

.create-button {
  position: fixed;
  bottom: 30px;
  right: 30px;
  z-index: 10;
}

.loading-container {
  padding: 20px;
}
</style>