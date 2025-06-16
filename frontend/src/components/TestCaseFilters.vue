<template>
  <div class="test-case-filters">
    <el-row :gutter="20">
      <el-col :xs="24" :sm="24" :md="10" :lg="10">
        <el-input
          v-model="searchModel"
          placeholder="Search tests by name, description or file path"
          clearable
          @input="updateSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </el-col>
      
      <el-col :xs="12" :sm="12" :md="7" :lg="7" v-if="testTypes">
        <el-select v-model="typeModel" placeholder="Test Type" @change="updateType" style="width: 100%">
          <el-option
            v-for="option in testTypes"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
      </el-col>
      
      <el-col :xs="12" :sm="12" :md="7" :lg="7" v-if="testStatuses">
        <el-select v-model="statusModel" placeholder="Status" @change="updateStatus" style="width: 100%">
          <el-option
            v-for="option in testStatuses"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { defineComponent, ref, watch } from 'vue'

export default defineComponent({
  name: 'TestCaseFilters',
  
  props: {
    search: {
      type: String,
      default: ''
    },
    type: {
      type: String,
      default: ''
    },
    status: {
      type: String,
      default: ''
    },
    testTypes: {
      type: Array,
      default: null
    },
    testStatuses: {
      type: Array,
      default: null
    }
  },
  
  emits: ['update:search', 'update:type', 'update:status'],
  
  setup(props, { emit }) {
    const searchModel = ref(props.search)
    const typeModel = ref(props.type)
    const statusModel = ref(props.status)
    
    // Watch for external changes
    watch(() => props.search, (val) => {
      searchModel.value = val
    })
    
    watch(() => props.type, (val) => {
      typeModel.value = val
    })
    
    watch(() => props.status, (val) => {
      statusModel.value = val
    })
    
    // Update functions
    const updateSearch = () => {
      emit('update:search', searchModel.value)
    }
    
    const updateType = () => {
      emit('update:type', typeModel.value)
    }
    
    const updateStatus = () => {
      emit('update:status', statusModel.value)
    }
    
    return {
      searchModel,
      typeModel,
      statusModel,
      updateSearch,
      updateType,
      updateStatus
    }
  }
})
</script>

<style scoped>
.test-case-filters {
  margin-bottom: 1.5rem;
}
</style> 