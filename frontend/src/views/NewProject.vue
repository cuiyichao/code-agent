<template>
  <div class="new-project-view">
    <el-row>
      <el-col :lg="24">
        <h1 class="page-title">Create New Project</h1>
        <p class="page-description">Add a new code repository for analysis</p>
      </el-col>
    </el-row>
    
    <!-- Error Alert -->
    <el-alert v-if="error" :title="error" type="error" show-icon class="mb-4" />
    
    <el-card shadow="hover" class="form-card">
      <el-form 
        ref="projectForm" 
        :model="formData" 
        :rules="rules" 
        label-position="top" 
        status-icon
      >
        <!-- Project Name -->
        <el-form-item label="Project Name" prop="name">
          <el-input 
            v-model="formData.name" 
            placeholder="Enter project name" 
            :disabled="loading" 
            clearable
          >
            <template #prefix>
              <el-icon><Document /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        
        <!-- Git URL -->
        <el-form-item label="Git Repository URL" prop="gitUrl">
          <el-input 
            v-model="formData.gitUrl" 
            placeholder="https://github.com/username/repository.git" 
            :disabled="loading || validatingRepo" 
            clearable
          >
            <template #prefix>
              <el-icon><Link /></el-icon>
            </template>
            <template #append>
              <el-button 
                :loading="validatingRepo" 
                :disabled="!formData.gitUrl || loading" 
                @click="validateRepository"
              >
                Validate
              </el-button>
            </template>
          </el-input>
          <small class="form-tip">
            <el-icon><InfoFilled /></el-icon>
            HTTPS URLs are recommended for better compatibility
          </small>
        </el-form-item>
        
        <!-- Branch Selection -->
        <el-form-item label="Branch" prop="branch" v-if="branches.length > 0">
          <el-select 
            v-model="formData.branch" 
            placeholder="Select branch" 
            :disabled="loading" 
            filterable
          >
            <el-option 
              v-for="branch in branches" 
              :key="branch" 
              :label="branch" 
              :value="branch" 
            />
          </el-select>
        </el-form-item>
        
        <!-- Description -->
        <el-form-item label="Description (optional)" prop="description">
          <el-input 
            v-model="formData.description" 
            type="textarea" 
            :rows="3" 
            placeholder="Enter project description" 
            :disabled="loading"
          />
        </el-form-item>
        
        <!-- Submit Button -->
        <el-form-item>
          <el-button 
            type="primary" 
            :loading="loading" 
            @click="submitForm" 
            :disabled="validatingRepo"
            class="submit-button"
          >
            Create Project
          </el-button>
          <el-button @click="resetForm" :disabled="loading || validatingRepo">
            Reset
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script>
import { ref, reactive } from 'vue'
import { useStore } from 'vuex'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { validateGitRepo, getRepoBranches } from '@/api/projects'

export default {
  name: 'NewProject',
  
  setup() {
    const store = useStore()
    const router = useRouter()
    const projectForm = ref(null)
    
    // Form data
    const formData = reactive({
      name: '',
      gitUrl: '',
      branch: 'main',
      description: ''
    })
    
    // Form validation rules
    const rules = {
      name: [
        { required: true, message: 'Project name is required', trigger: 'blur' },
        { min: 3, max: 50, message: 'Length should be 3 to 50 characters', trigger: 'blur' }
      ],
      gitUrl: [
        { required: true, message: 'Git URL is required', trigger: 'blur' },
        { pattern: /^(https?:\/\/|git@)[\w.-]+[/:][\w.-]+\/[\w.-]+\.git$/, message: 'Please enter a valid Git URL', trigger: 'blur' }
      ],
      branch: [
        { required: true, message: 'Branch is required', trigger: 'change' }
      ]
    }
    
    // State
    const loading = ref(false)
    const validatingRepo = ref(false)
    const error = ref(null)
    const branches = ref([])
    
    // Validate Git Repository
    const validateRepository = async () => {
      if (!formData.gitUrl) {
        ElMessage.warning('Please enter a Git URL first')
        return
      }
      
      validatingRepo.value = true
      error.value = null
      
      try {
        // Validate repository
        await validateGitRepo(formData.gitUrl)
        
        // If validation succeeds, fetch branches
        const branchesData = await getRepoBranches(formData.gitUrl)
        branches.value = branchesData
        
        // Set default branch if available
        if (branchesData.includes('main')) {
          formData.branch = 'main'
        } else if (branchesData.includes('master')) {
          formData.branch = 'master'
        } else if (branchesData.length > 0) {
          formData.branch = branchesData[0]
        }
        
        ElMessage.success('Repository is valid')
      } catch (err) {
        error.value = err.message || 'Failed to validate repository'
        ElMessage.error(error.value)
      } finally {
        validatingRepo.value = false
      }
    }
    
    // Submit form
    const submitForm = async () => {
      if (!projectForm.value) return
      
      await projectForm.value.validate(async (valid) => {
        if (!valid) {
          ElMessage.warning('Please fix the form errors')
          return
        }
        
        loading.value = true
        error.value = null
        
        try {
          // Create project
          await store.dispatch('projects/createNewProject', {
            name: formData.name,
            git_url: formData.gitUrl,
            branch: formData.branch,
            description: formData.description
          })
          
          ElMessage.success('Project created successfully')
          router.push('/')
        } catch (err) {
          error.value = err.message || 'Failed to create project'
          ElMessage.error(error.value)
        } finally {
          loading.value = false
        }
      })
    }
    
    // Reset form
    const resetForm = () => {
      if (projectForm.value) {
        projectForm.value.resetFields()
        branches.value = []
      }
    }
    
    return {
      projectForm,
      formData,
      rules,
      loading,
      validatingRepo,
      error,
      branches,
      validateRepository,
      submitForm,
      resetForm
    }
  }
}
</script>

<style scoped>
.new-project-view {
  max-width: 800px;
  margin: 0 auto;
}

.form-card {
  margin-top: 1.5rem;
  padding: 1rem;
}

.form-tip {
  display: flex;
  align-items: center;
  color: var(--text-secondary);
  font-size: 0.85rem;
  margin-top: 0.5rem;
}

.form-tip i {
  margin-right: 0.5rem;
  color: var(--info-color);
}

.submit-button {
  min-width: 120px;
}
</style>