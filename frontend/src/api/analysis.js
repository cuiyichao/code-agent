import http from './http'

/**
 * Get analysis results for a project
 * @param {string|number} projectId - Project ID
 */
export const getAnalysisResults = (projectId) => {
  return http.get(`/projects/${projectId}/analysis`)
}

/**
 * Get test cases for a project
 * @param {string|number} projectId - Project ID
 */
export const getTestCases = (projectId) => {
  return http.get(`/projects/${projectId}/test-cases`)
}

/**
 * Get code changes with diff
 * @param {string|number} projectId - Project ID
 */
export const getCodeDiff = (projectId) => {
  return http.get(`/projects/${projectId}/diff`)
}

/**
 * Get impact analysis for a specific file
 * @param {string|number} projectId - Project ID
 * @param {string} filePath - File path
 */
export const getFileImpact = (projectId, filePath) => {
  return http.get(`/projects/${projectId}/impact`, {
    params: { filePath }
  })
}

/**
 * Export test cases as file
 * @param {string|number} projectId - Project ID
 * @param {string} format - Export format (e.g., 'json', 'xml')
 */
export const exportTestCases = (projectId, format = 'json') => {
  return http.get(`/projects/${projectId}/test-cases/export`, {
    params: { format },
    responseType: 'blob'
  })
} 