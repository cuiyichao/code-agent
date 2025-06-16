import { getProjects, getProjectById, createProject, analyzeProject } from '@/api/projects'

export default {
  namespaced: true,
  
  state: () => ({
    list: [],
    currentProject: null,
    loading: false,
    error: null
  }),
  
  mutations: {
    SET_PROJECTS(state, projects) {
      state.list = projects
    },
    SET_CURRENT_PROJECT(state, project) {
      state.currentProject = project
    },
    SET_LOADING(state, status) {
      state.loading = status
    },
    SET_ERROR(state, error) {
      state.error = error
    }
  },
  
  actions: {
    async fetchProjects({ commit }) {
      commit('SET_LOADING', true)
      try {
        const projects = await getProjects()
        commit('SET_PROJECTS', projects)
      } catch (error) {
        commit('SET_ERROR', error.message)
      } finally {
        commit('SET_LOADING', false)
      }
    },
    
    async fetchProjectById({ commit }, id) {
      commit('SET_LOADING', true)
      try {
        const project = await getProjectById(id)
        commit('SET_CURRENT_PROJECT', project)
      } catch (error) {
        commit('SET_ERROR', error.message)
      } finally {
        commit('SET_LOADING', false)
      }
    },
    
    async createNewProject({ commit }, projectData) {
      commit('SET_LOADING', true)
      try {
        const result = await createProject(projectData)
        return result
      } catch (error) {
        commit('SET_ERROR', error.message)
        throw error
      } finally {
        commit('SET_LOADING', false)
      }
    },
    
    async runAnalysis({ commit }, id) {
      commit('SET_LOADING', true)
      try {
        const result = await analyzeProject(id)
        return result
      } catch (error) {
        commit('SET_ERROR', error.message)
        throw error
      } finally {
        commit('SET_LOADING', false)
      }
    }
  },
  
  getters: {
    getProjectById: state => id => {
      return state.list.find(project => project.id === id)
    },
    isLoading: state => state.loading,
    hasError: state => !!state.error
  }
} 