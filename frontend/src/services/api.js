import axios from 'axios';

// 配置API基础URL
const API_BASE_URL = 'http://localhost:5000/api';

/**
 * 创建新项目
 * @param {Object} projectData - 项目数据
 * @param {string} projectData.name - 项目名称
 * @param {string} projectData.git_url - Git仓库URL
 * @returns {Promise<Object>} 创建的项目信息
 */
export const createProject = async (projectData) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/projects`, projectData);
    return response.data;
  } catch (error) {
    console.error('API Error: 创建项目失败', error);
    throw error;
  }
};

/**
 * 获取所有项目列表
 * @returns {Promise<Array>} 项目列表
 */
export const getProjects = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/projects`);
    return response.data;
  } catch (error) {
    console.error('API Error: 获取项目列表失败', error);
    throw error;
  }
};

/**
 * 获取项目详情（包含代码变更和测试用例）
 * @param {number|string} projectId - 项目ID
 * @returns {Promise<Object>} 项目详情数据
 */
export const getProjectDetails = async (projectId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/projects/${projectId}`);
    return response.data;
  } catch (error) {
    console.error(`API Error: 获取项目 ${projectId} 详情失败`, error);
    throw error;
  }
};

/**
 * 触发代码变更分析
 * @param {number|string} projectId - 项目ID
 * @param {string} commitHash - 提交哈希
 * @returns {Promise<Object>} 分析结果
 */
export const analyzeCodeChanges = async (projectId, commitHash) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/projects/${projectId}/analyze`, {
      commit_hash: commitHash
    });
    return response.data;
  } catch (error) {
    console.error(`API Error: 分析项目 ${projectId} 代码变更失败`, error);
    throw error;
  }
};

/**
 * 获取项目的代码变更历史
 * @param {number|string} projectId - 项目ID
 * @returns {Promise<Array>} 代码变更历史列表
 */
export const getCodeChanges = async (projectId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/projects/${projectId}/changes`);
    return response.data;
  } catch (error) {
    console.error(`API Error: 获取项目 ${projectId} 代码变更历史失败`, error);
    throw error;
  }
};

/**
 * 获取特定代码变更的测试用例
 * @param {number|string} changeId - 代码变更ID
 * @returns {Promise<Array>} 测试用例列表
 */
export const getTestCases = async (changeId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/changes/${changeId}/test-cases`);
    return response.data;
  } catch (error) {
    console.error(`API Error: 获取代码变更 ${changeId} 的测试用例失败`, error);
    throw error;
  }
};