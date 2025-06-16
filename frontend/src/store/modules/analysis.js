import { getAnalysisResults, getTestCases } from '@/api/analysis'

export default {
  namespaced: true,
  
  state: () => ({
    results: {},
    testCases: {},
    loading: false,
    error: null
  }),
  
  mutations: {
    SET_ANALYSIS_RESULTS(state, { projectId, results }) {
      state.results = { ...state.results, [projectId]: results }
    },
    SET_TEST_CASES(state, { projectId, testCases }) {
      state.testCases = { ...state.testCases, [projectId]: testCases }
    },
    SET_LOADING(state, status) {
      state.loading = status
    },
    SET_ERROR(state, error) {
      state.error = error
    }
  },
  
  actions: {
    async fetchAnalysisResults({ commit }, projectId) {
      commit('SET_LOADING', true)
      try {
        const results = await getAnalysisResults(projectId)
        commit('SET_ANALYSIS_RESULTS', { projectId, results })
      } catch (error) {
        commit('SET_ERROR', error.message)
      } finally {
        commit('SET_LOADING', false)
      }
    },
    
    async fetchTestCases({ commit }, projectId) {
      commit('SET_LOADING', true)
      try {
        const testCases = await getTestCases(projectId)
        commit('SET_TEST_CASES', { projectId, testCases })
      } catch (error) {
        commit('SET_ERROR', error.message)
      } finally {
        commit('SET_LOADING', false)
      }
    }
  },
  
  getters: {
    getResultsForProject: state => projectId => {
      return state.results[projectId] || null
    },
    getTestCasesForProject: state => projectId => {
      return state.testCases[projectId] || []
    },
    isLoading: state => state.loading,
    hasError: state => !!state.error
  }
} 