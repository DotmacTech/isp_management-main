/**
 * Utility functions for formatting data in the frontend
 */

/**
 * Format bytes to a human-readable string with appropriate unit
 * @param {number} bytes - The number of bytes to format
 * @param {number} decimals - The number of decimal places to show
 * @returns {string} Formatted string with appropriate unit
 */
export const formatBytes = (bytes, decimals = 2) => {
  if (bytes === 0) return '0 Bytes';
  if (bytes === null || bytes === undefined) return 'N/A';
  
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

/**
 * Format a date string to a human-readable format
 * @param {string} dateString - The date string to format
 * @returns {string} Formatted date string
 */
export const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  
  const date = new Date(dateString);
  
  if (isNaN(date.getTime())) return 'Invalid Date';
  
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
};

/**
 * Format a currency value
 * @param {number} value - The currency value to format
 * @param {string} currency - The currency code (default: USD)
 * @returns {string} Formatted currency string
 */
export const formatCurrency = (value, currency = 'USD') => {
  if (value === null || value === undefined) return 'N/A';
  
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency
  }).format(value);
};

/**
 * Format a speed value in Mbps
 * @param {number} speed - The speed value in Mbps
 * @returns {string} Formatted speed string
 */
export const formatSpeed = (speed) => {
  if (speed === null || speed === undefined) return 'N/A';
  
  return `${speed} Mbps`;
};

/**
 * Format a percentage value
 * @param {number} value - The percentage value
 * @param {number} decimals - The number of decimal places to show
 * @returns {string} Formatted percentage string
 */
export const formatPercentage = (value, decimals = 1) => {
  if (value === null || value === undefined) return 'N/A';
  
  return `${value.toFixed(decimals)}%`;
};

/**
 * Format a duration in seconds to a human-readable string
 * @param {number} seconds - The duration in seconds
 * @returns {string} Formatted duration string
 */
export const formatDuration = (seconds) => {
  if (seconds === null || seconds === undefined) return 'N/A';
  
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  
  const parts = [];
  
  if (days > 0) parts.push(`${days}d`);
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (remainingSeconds > 0 || parts.length === 0) parts.push(`${remainingSeconds}s`);
  
  return parts.join(' ');
};

/**
 * Format a billing cycle string to a more readable form
 * @param {string} cycle - The billing cycle string
 * @returns {string} Formatted billing cycle string
 */
export const formatBillingCycle = (cycle) => {
  if (!cycle) return 'N/A';
  
  const cycles = {
    'monthly': 'Month',
    'quarterly': 'Quarter',
    'biannual': 'Half Year',
    'annual': 'Year'
  };
  
  return cycles[cycle.toLowerCase()] || cycle;
};

/**
 * Format a status string to a more readable form with proper capitalization
 * @param {string} status - The status string
 * @returns {string} Formatted status string
 */
export const formatStatus = (status) => {
  if (!status) return 'N/A';
  
  return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
};

/**
 * Get appropriate color for a status
 * @param {string} status - The status string
 * @returns {string} Color name for the status
 */
export const getStatusColor = (status) => {
  if (!status) return 'default';
  
  const statusLower = status.toLowerCase();
  
  const statusColors = {
    'active': 'success',
    'pending': 'warning',
    'suspended': 'error',
    'cancelled': 'error',
    'throttled': 'warning',
    'expired': 'error',
    'processing': 'info'
  };
  
  return statusColors[statusLower] || 'default';
};

/**
 * Format a feature name to a more readable form
 * @param {string} feature - The feature name
 * @returns {string} Formatted feature name
 */
export const formatFeatureName = (feature) => {
  if (!feature) return '';
  
  return feature
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};
