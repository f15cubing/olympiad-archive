/**
 * Service for interacting with AI tagging API endpoints.
 */

const API_BASE_URL = "http://localhost:8000";

/**
 * Tag a single problem using AI.
 * @param {number} problemId - The ID of the problem to tag
 * @returns {Promise<Object>} - Tagging result with metadata
 */
export async function tagSingleProblem(problemId) {
  try {
    const response = await fetch(`${API_BASE_URL}/tagging/${problemId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.detail || `HTTP ${response.status}: Failed to tag problem`
      );
    }

    return await response.json();
  } catch (error) {
    console.error("Error tagging problem:", error);
    throw error;
  }
}

/**
 * Tag multiple problems in a batch using AI.
 * @param {number[]} problemIds - List of problem IDs to tag
 * @returns {Promise<Object>} - Batch tagging result
 */
export async function tagMultipleProblems(problemIds) {
  try {
    const response = await fetch(`${API_BASE_URL}/tagging/batch`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ problem_ids: problemIds }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.detail || `HTTP ${response.status}: Failed to tag problems`
      );
    }

    return await response.json();
  } catch (error) {
    console.error("Error tagging problems:", error);
    throw error;
  }
}
