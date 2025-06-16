<template>
  <el-card class="project-card h-full" shadow="hover">
    <div class="project-card-header">
      <h3 class="project-name">{{ project.name }}</h3>
      <el-tag :type="riskLevelTag" size="small">
        {{ riskLevelText }}
      </el-tag>
    </div>

    <div class="project-meta">
      <div class="meta-item">
        <el-icon><Calendar /></el-icon>
        <span>{{ formattedDate }}</span>
      </div>
      <div class="meta-item">
        <el-icon><Link /></el-icon>
        <el-tooltip :content="project.git_url" placement="top">
          <span class="git-url">{{ truncatedUrl }}</span>
        </el-tooltip>
      </div>
    </div>

    <div class="project-stats">
      <div class="stat-item">
        <span class="stat-label">Files</span>
        <span class="stat-value">{{ project.stats?.files_count || 0 }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Changes</span>
        <span class="stat-value">{{ project.stats?.changes_count || 0 }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Tests</span>
        <span class="stat-value">{{ project.stats?.tests_count || 0 }}</span>
      </div>
    </div>

    <div class="project-actions">
      <router-link :to="{ name: 'ProjectDetail', params: { id: project.id } }">
        <el-button type="primary" text>View Details</el-button>
      </router-link>
      <router-link :to="{ name: 'ProjectAnalysis', params: { id: project.id } }">
        <el-button type="success" text>Analysis</el-button>
      </router-link>
    </div>
  </el-card>
</template>

<script>
import { computed } from 'vue'
import { formatDate, truncateText } from '@/utils/formatters'

export default {
  name: 'ProjectCard',
  
  props: {
    project: {
      type: Object,
      required: true
    }
  },
  
  setup(props) {
    // Format date
    const formattedDate = computed(() => formatDate(props.project.created_at))
    
    // Truncate URL
    const truncatedUrl = computed(() => truncateText(props.project.git_url, 30))
    
    // Risk level tag and text
    const riskLevelTag = computed(() => {
      const levels = {
        0: 'success',
        1: 'info',
        2: 'warning',
        3: 'danger'
      }
      return levels[props.project.risk_level] || 'info'
    })
    
    const riskLevelText = computed(() => {
      const levels = {
        0: 'No Risk',
        1: 'Low',
        2: 'Medium',
        3: 'High'
      }
      return levels[props.project.risk_level] || 'Unknown'
    })
    
    return {
      formattedDate,
      truncatedUrl,
      riskLevelTag,
      riskLevelText
    }
  }
}
</script>

<style scoped>
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
  color: var(--text-secondary);
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
  color: var(--text-secondary);
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
</style> 