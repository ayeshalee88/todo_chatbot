const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ApiResult<T> = {
  data?: T;
  error?: string;
};

export const apiClient = {
  // GET TASKS
  async getTasks(userId: string): Promise<ApiResult<any[]>> {
    try {
      const res = await fetch(`${API_URL}/api/users/${userId}/tasks`);

      if (!res.ok) {
        return { error: `Failed to fetch tasks: ${res.status}` };
      }

      const data = await res.json();
      return { data };
    } catch (err) {
      return { error: 'Network error while fetching tasks' };
    }
  },

  // CREATE TASK
  async createTask(userId: string, task: any): Promise<ApiResult<any>> {
    try {
      const res = await fetch(`${API_URL}/api/users/${userId}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(task),
      });

      if (!res.ok) {
        return { error: `Failed to create task: ${res.status}` };
      }

      const data = await res.json();
      return { data };
    } catch (err) {
      return { error: 'Network error while creating task' };
    }
  },

  // UPDATE TASK
  async updateTask(
    userId: string,
    taskId: string,
    task: any
  ): Promise<ApiResult<any>> {
    try {
      const res = await fetch(
        `${API_URL}/api/users/${userId}/tasks/${taskId}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(task),
        }
      );

      if (!res.ok) {
        return { error: `Failed to update task: ${res.status}` };
      }

      const data = await res.json();
      return { data };
    } catch (err) {
      return { error: 'Network error while updating task' };
    }
  },

  // DELETE TASK
  async deleteTask(
    userId: string,
    taskId: string
  ): Promise<ApiResult<null>> {
    try {
      const res = await fetch(
        `${API_URL}/api/users/${userId}/tasks/${taskId}`,
        { method: 'DELETE' }
      );

      if (!res.ok) {
        return { error: `Failed to delete task: ${res.status}` };
      }

      return { data: null };
    } catch (err) {
      return { error: 'Network error while deleting task' };
    }
  },

  // TOGGLE COMPLETE
  async updateTaskCompletion(
    userId: string,
    taskId: string,
    completed: boolean
  ): Promise<ApiResult<any>> {
    try {
      const res = await fetch(
        `${API_URL}/api/users/${userId}/tasks/${taskId}/complete`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ completed }),
        }
      );

      if (!res.ok) {
        return { error: `Failed to update task: ${res.status}` };
      }

      const data = await res.json();
      return { data };
    } catch (err) {
      return { error: 'Network error while updating completion' };
    }
  },
};
