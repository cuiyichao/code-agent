import moment from 'moment'

/**
 * Format date with moment.js
 * @param {string|Date} date - Date to format
 * @param {string} format - Format string (default: 'YYYY-MM-DD HH:mm:ss')
 */
export const formatDate = (date, format = 'YYYY-MM-DD HH:mm:ss') => {
  if (!date) return '-'
  return moment(date).format(format)
}

/**
 * Format relative date (e.g., "2 hours ago")
 * @param {string|Date} date - Date to format
 */
export const formatRelativeDate = (date) => {
  if (!date) return '-'
  return moment(date).fromNow()
}

/**
 * Format bytes to human-readable size
 * @param {number} bytes - Bytes to format
 * @param {number} decimals - Number of decimals
 */
export const formatBytes = (bytes, decimals = 2) => {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + ' ' + sizes[i]
}

/**
 * Truncate text with ellipsis
 * @param {string} text - Text to truncate
 * @param {number} length - Max length
 */
export const truncateText = (text, length = 30) => {
  if (!text) return ''
  if (text.length <= length) return text
  
  return text.substring(0, length) + '...'
}

/**
 * Format risk level with label and color
 * @param {string|number} level - Risk level
 */
export const formatRiskLevel = (level) => {
  const levels = {
    0: { label: 'No Risk', color: '#67C23A' },
    1: { label: 'Low', color: '#409EFF' },
    2: { label: 'Medium', color: '#E6A23C' },
    3: { label: 'High', color: '#F56C6C' }
  }
  
  return levels[level] || { label: 'Unknown', color: '#909399' }
}

/**
 * Get programming language from filename
 * @param {string} filename - Filename with extension
 * @returns {string} - Language identifier for syntax highlighting
 */
export const getLanguageFromFilename = (filename) => {
  if (!filename) return 'plaintext'

  const extension = filename.split('.').pop().toLowerCase()
  
  const extensionMap = {
    // JavaScript and TypeScript
    'js': 'javascript',
    'jsx': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
    
    // Web
    'html': 'html',
    'xml': 'xml',
    'css': 'css',
    'scss': 'scss',
    'less': 'less',
    
    // Python
    'py': 'python',
    'pyw': 'python',
    
    // Java
    'java': 'java',
    
    // C-family
    'c': 'c',
    'cpp': 'cpp',
    'cc': 'cpp',
    'h': 'cpp',
    'hpp': 'cpp',
    'cs': 'csharp',
    
    // Go
    'go': 'go',
    
    // Ruby
    'rb': 'ruby',
    
    // PHP
    'php': 'php',
    
    // Shell
    'sh': 'shell',
    'bash': 'shell',
    
    // JSON and configs
    'json': 'json',
    'yml': 'yaml',
    'yaml': 'yaml',
    'toml': 'ini',
    'ini': 'ini',
    
    // Markdown and documentation
    'md': 'markdown',
    'markdown': 'markdown',
    
    // Other
    'sql': 'sql',
    'swift': 'swift',
    'kt': 'kotlin',
    'rs': 'rust',
    'dart': 'dart'
  }
  
  return extensionMap[extension] || 'plaintext'
} 