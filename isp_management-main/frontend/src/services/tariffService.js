import axios from 'axios';
import { handleApiError } from '../utils/errorHandlers';
import { authHeader } from '../utils/authHeader';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/**
 * Service for interacting with the Tariff Enforcement Module API
 */
export const tariffService = {
  /**
   * Get all available tariff plans
   * @returns {Promise<Array>} List of tariff plans
   */
  getAllTariffPlans: async () => {
    try {
      const response = await axios.get(`${API_URL}/tariff/plans`, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to fetch tariff plans');
    }
  },

  /**
   * Get a specific tariff plan by ID
   * @param {number} planId - The ID of the tariff plan
   * @returns {Promise<Object>} Tariff plan details
   */
  getTariffPlan: async (planId) => {
    try {
      const response = await axios.get(`${API_URL}/tariff/plans/${planId}`, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to fetch tariff plan');
    }
  },

  /**
   * Create a new tariff plan (admin only)
   * @param {Object} planData - The tariff plan data
   * @returns {Promise<Object>} Created tariff plan
   */
  createTariffPlan: async (planData) => {
    try {
      const response = await axios.post(`${API_URL}/tariff/plans`, planData, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to create tariff plan');
    }
  },

  /**
   * Update an existing tariff plan (admin only)
   * @param {number} planId - The ID of the tariff plan
   * @param {Object} planData - The updated tariff plan data
   * @returns {Promise<Object>} Updated tariff plan
   */
  updateTariffPlan: async (planId, planData) => {
    try {
      const response = await axios.put(`${API_URL}/tariff/plans/${planId}`, planData, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to update tariff plan');
    }
  },

  /**
   * Delete a tariff plan (admin only)
   * @param {number} planId - The ID of the tariff plan
   * @returns {Promise<Object>} Response with status and message
   */
  deleteTariffPlan: async (planId) => {
    try {
      const response = await axios.delete(`${API_URL}/tariff/plans/${planId}`, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to delete tariff plan');
    }
  },

  /**
   * Assign a tariff plan to a user (admin only)
   * @param {number} planId - The ID of the tariff plan
   * @param {Object} assignmentData - The assignment data
   * @returns {Promise<Object>} Response with status and message
   */
  assignPlanToUser: async (planId, assignmentData) => {
    try {
      const response = await axios.post(`${API_URL}/tariff/plans/${planId}/assign`, assignmentData, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to assign tariff plan');
    }
  },

  /**
   * Get the active tariff plan for a user
   * @param {number} userId - The ID of the user
   * @returns {Promise<Object>} User's active tariff plan
   */
  getUserTariffPlan: async (userId) => {
    try {
      const response = await axios.get(`${API_URL}/tariff/users/${userId}/plan`, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to fetch user tariff plan');
    }
  },

  /**
   * Update a user's tariff plan
   * @param {number} userId - The ID of the user
   * @param {number} planId - The ID of the tariff plan
   * @param {Object} updateData - The update data
   * @returns {Promise<Object>} Response with status and message
   */
  updateUserTariffPlan: async (userId, planId, updateData) => {
    try {
      const response = await axios.put(`${API_URL}/tariff/users/${userId}/plan/${planId}`, updateData, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to update user tariff plan');
    }
  },

  /**
   * Cancel a user's active tariff plan
   * @param {number} userId - The ID of the user
   * @returns {Promise<Object>} Response with status and message
   */
  cancelUserTariffPlan: async (userId) => {
    try {
      const response = await axios.delete(`${API_URL}/tariff/users/${userId}/plan`, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to cancel user tariff plan');
    }
  },

  /**
   * Change a user's tariff plan
   * @param {number} userId - The ID of the user
   * @param {number} newPlanId - The ID of the new tariff plan
   * @param {Date} effectiveDate - Optional effective date for the change
   * @returns {Promise<Object>} Response with status and message
   */
  changeTariffPlan: async (userId, newPlanId, effectiveDate = null) => {
    try {
      const data = {
        new_plan_id: newPlanId,
        effective_date: effectiveDate
      };
      const response = await axios.post(`${API_URL}/tariff/users/${userId}/change-plan`, data, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to change tariff plan');
    }
  },

  /**
   * Record usage data for a user's tariff plan
   * @param {Object} usageData - The usage data
   * @returns {Promise<Object>} Response with status and message
   */
  recordUsage: async (usageData) => {
    try {
      const response = await axios.post(`${API_URL}/tariff/usage/record`, usageData, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to record usage data');
    }
  },

  /**
   * Check a user's usage against their plan limits
   * @param {Object} checkData - The check data
   * @returns {Promise<Object>} Usage check result
   */
  checkUsage: async (checkData) => {
    try {
      const response = await axios.post(`${API_URL}/tariff/usage/check`, checkData, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to check usage');
    }
  },

  /**
   * Get the bandwidth policy for a user
   * @param {number} userId - The ID of the user
   * @returns {Promise<Object>} User's bandwidth policy
   */
  getUserBandwidthPolicy: async (userId) => {
    try {
      const response = await axios.get(`${API_URL}/tariff/users/${userId}/bandwidth-policy`, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to fetch bandwidth policy');
    }
  },

  /**
   * Reset the usage cycle for a user's tariff plan
   * @param {number} userId - The ID of the user
   * @returns {Promise<Object>} Response with status and message
   */
  resetUsageCycle: async (userId) => {
    try {
      const response = await axios.post(`${API_URL}/tariff/users/${userId}/reset-cycle`, {}, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to reset usage cycle');
    }
  },

  /**
   * Process scheduled tariff plan changes (admin only)
   * @returns {Promise<Object>} Response with status and results
   */
  processScheduledChanges: async () => {
    try {
      const response = await axios.post(`${API_URL}/tariff/process-scheduled-changes`, {}, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to process scheduled changes');
    }
  },

  /**
   * Calculate overage fees for a user
   * @param {number} userId - The ID of the user
   * @param {number} usageMb - The usage in MB
   * @returns {Promise<Object>} Overage fee calculation
   */
  calculateOverageFee: async (userId, usageMb) => {
    try {
      const response = await axios.post(`${API_URL}/tariff/users/${userId}/calculate-overage`, { usage_mb: usageMb }, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to calculate overage fee');
    }
  },

  /**
   * Check if a user has crossed the FUP threshold
   * @param {Object} checkData - The check data
   * @returns {Promise<Object>} FUP check result
   */
  checkFUPThreshold: async (checkData) => {
    try {
      const response = await axios.post(`${API_URL}/tariff/check-fup`, checkData, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to check FUP threshold');
    }
  },

  /**
   * Get usage history for a user
   * @param {number} userId - The ID of the user
   * @param {Object} params - Optional query parameters
   * @returns {Promise<Array>} User's usage history
   */
  getUserUsageHistory: async (userId, params = {}) => {
    try {
      const response = await axios.get(`${API_URL}/tariff/users/${userId}/usage-history`, { 
        headers: authHeader(),
        params
      });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to fetch usage history');
    }
  },

  /**
   * Get scheduled plan changes for a user
   * @param {number} userId - The ID of the user
   * @returns {Promise<Array>} User's scheduled plan changes
   */
  getUserScheduledChanges: async (userId) => {
    try {
      const response = await axios.get(`${API_URL}/tariff/users/${userId}/scheduled-changes`, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to fetch scheduled changes');
    }
  },

  /**
   * Cancel a scheduled plan change
   * @param {number} changeId - The ID of the scheduled change
   * @returns {Promise<Object>} Response with status and message
   */
  cancelScheduledChange: async (changeId) => {
    try {
      const response = await axios.delete(`${API_URL}/tariff/scheduled-changes/${changeId}`, { headers: authHeader() });
      return response.data;
    } catch (error) {
      throw handleApiError(error, 'Failed to cancel scheduled change');
    }
  }
};

export default tariffService;
