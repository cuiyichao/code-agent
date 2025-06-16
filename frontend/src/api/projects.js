import http from './http'

/**
 * Get all projects
 */
export const getProjects = () => {
  return http.get('/projects')
}

/**
 * Get project by ID
 * @param {string|number} id - Project ID
 */
export const getProjectById = (id) => {
  return http.get(`/projects/${id}`)
}

/**
 * Create a new project
 * @param {Object} projectData - Project data
 */
export const createProject = (projectData) => {
  return http.post('/projects', projectData)
}

/**
 * Update project
 * @param {string|number} id - Project ID
 * @param {Object} projectData - Project data to update
 */
export const updateProject = (id, projectData) => {
  return http.put(`/projects/${id}`, projectData)
}

/**
 * Delete project
 * @param {string|number} id - Project ID
 */
export const deleteProject = (id) => {
  return http.delete(`/projects/${id}`)
}

/**
 * Start project analysis
 * @param {string|number} id - Project ID
 */
export const analyzeProject = (id) => {
  return http.post(`/projects/${id}/analyze`)
}

/**
 * Validate Git repository
 * @param {string} repoUrl - Repository URL
 */
export const validateGitRepo = (repoUrl) => {
  return http.post('/projects/validate-repo', { repoUrl })
}

/**
 * Get available branches for repository
 * @param {string} repoUrl - Repository URL
 */
export const getRepoBranches = (repoUrl) => {
  return http.get('/projects/repo-branches', { params: { repoUrl } })
} 