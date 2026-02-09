"""
MCP Server for Todo AI Chatbot
Exposes task operations as tools for OpenAI Agents
"""
import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from sqlmodel import Session, select
from datetime import datetime
from shared_database import get_session
from backend.models.task_models import Task, TaskCreate, TaskUpdate, TaskResponse


# Global variable to hold the session
db_session: Optional[Session] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_session
    # Startup: Initialize the database session
    session_generator = get_session()
    db_session = next(session_generator)
    yield
    # Shutdown: Close the session
    if db_session:
        db_session.close()


app = FastAPI(lifespan=lifespan)


def get_user_tasks(user_id: str) -> List[Task]:
    """Get all tasks for a specific user"""
    if not db_session:
        raise HTTPException(status_code=500, detail="Database session not available")

    statement = select(Task).where(Task.user_id == user_id)
    tasks = db_session.exec(statement).all()
    return tasks


def get_task_by_position(user_id: str, position: int) -> Tuple[Task, int]:
    """Get a specific task by its position in the user's task list (1-indexed)"""
    if not db_session:
        raise HTTPException(status_code=500, detail="Database session not available")

    tasks = get_user_tasks(user_id)
    
    if position < 1 or position > len(tasks):
        raise HTTPException(status_code=404, detail=f"Task at position {position} not found")
    
    # Return the task at the specified position (1-indexed) and its actual index
    return tasks[position - 1], position - 1


def get_task_by_id(task_id: str, user_id: str) -> Task:
    """Get a specific task for a user"""
    if not db_session:
        raise HTTPException(status_code=500, detail="Database session not available")

    statement = select(Task).where(Task.id == task_id, Task.user_id == user_id)
    task = db_session.exec(statement).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")
    return task


@app.post("/tools/add_task")
async def add_task_tool(
    title: str = Query(..., description="Task title"),
    description: str = Query("", description="Task description"),
    user_id: str = Query(..., description="User ID to associate with the task")
) -> Dict[str, Any]:
    """
    Add a new task
    Args:
        title: Task title (required)
        description: Task description (optional)
        user_id: User ID to associate with the task
    Returns:
        Created task object
    """
    print(f"DEBUG: add_task_tool called with - title: '{title}', description: '{description}', user_id: '{user_id}'")
    
    try:
        if not title or not title.strip():
            print(f"DEBUG: Validation failed - title is empty or blank")
            raise HTTPException(status_code=400, detail="Title is required")

        if not user_id:
            print(f"DEBUG: Validation failed - user_id is empty")
            raise HTTPException(status_code=400, detail="User ID is required")

        if not db_session:
            print(f"DEBUG: Database session not available")
            raise HTTPException(status_code=500, detail="Database session not available")

        print(f"DEBUG: Attempting to create task for user_id: '{user_id}'")
        
        # Create the task
        db_task = Task(
            title=title,
            description=description,
            user_id=user_id,
            completed=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db_session.add(db_task)
        db_session.commit()
        db_session.refresh(db_task)
        
        print(f"DEBUG: Task created successfully - ID: {db_task.id}, Title: '{db_task.title}', User ID: '{db_task.user_id}'")
        
        # Convert to response format
        task_response = TaskResponse(
            id=db_task.id,
            title=db_task.title,
            description=db_task.description,
            completed=db_task.completed,
            user_id=db_task.user_id,
            created_at=db_task.created_at,
            updated_at=db_task.updated_at
        )

        return {"success": True, "task": task_response.dict()}
    except Exception as e:
        print(f"FULL ERROR in add_task_tool: {str(e)}")
        import traceback
        traceback.print_exc()
        db_session.rollback()  # Rollback in case of error
        raise HTTPException(status_code=500, detail=f"Error creating task: {str(e)}")


@app.post("/tools/list_tasks")
async def list_tasks_tool(user_id: str = Query(..., description="User ID to filter tasks")) -> Dict[str, Any]:
    """
    List all tasks for a user
    Args:
        user_id: User ID to filter tasks
    Returns:
        List of tasks with position numbers and summary statistics
    """
    print(f"DEBUG: list_tasks_tool called with user_id: '{user_id}'")
    
    try:
        if not user_id:
            print(f"DEBUG: Validation failed - user_id is empty")
            raise HTTPException(status_code=400, detail="User ID is required")

        if not db_session:
            print(f"DEBUG: Database session not available")
            raise HTTPException(status_code=500, detail="Database session not available")

        tasks = get_user_tasks(user_id)
        print(f"DEBUG: Found {len(tasks)} tasks for user_id: '{user_id}'")

        # Separate tasks by completion status
        pending_tasks = []
        completed_tasks = []
        
        for idx, task in enumerate(tasks, 1):
            task_data = TaskResponse(
                id=task.id,
                title=task.title,
                description=task.description,
                completed=task.completed,
                user_id=task.user_id,
                created_at=task.created_at,
                updated_at=task.updated_at
            ).dict()
            # Add position number to the task data
            task_data['position'] = idx
            
            if task.completed:
                completed_tasks.append(task_data)
            else:
                pending_tasks.append(task_data)

        # Convert tasks to response format with position numbers
        task_list = []
        for task in pending_tasks:
            task_list.append(task)
        for task in completed_tasks:
            task_list.append(task)

        print(f"DEBUG: Returning {len(task_list)} tasks with {len(pending_tasks)} pending and {len(completed_tasks)} completed")

        # Return structured data with summary information
        return {
            "success": True, 
            "tasks": task_list,
            "summary": {
                "total": len(tasks),
                "pending": len(pending_tasks),
                "completed": len(completed_tasks)
            },
            "pending_tasks": pending_tasks,
            "completed_tasks": completed_tasks
        }
    except Exception as e:
        print(f"FULL ERROR in list_tasks_tool: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error retrieving tasks: {str(e)}")


@app.post("/tools/update_task")
async def update_task_tool(
    task_position: int = Query(..., ge=1, description="Position of the task in the user's task list (1-indexed)"),
    user_id: str = Query(..., description="User ID to validate ownership"),
    title: str = Query(None, description="New title (optional)"),
    description: str = Query(None, description="New description (optional)")
) -> Dict[str, Any]:
    """
    Update an existing task by position
    Args:
        task_position: Position of the task in the user's task list (1-indexed)
        user_id: User ID to validate ownership
        title: New title (optional)
        description: New description (optional)
    Returns:
        Updated task object
    """
    print(f"DEBUG: update_task_tool called with task_position: {task_position}, user_id: '{user_id}', title: '{title}', description: '{description}'")
    
    try:
        if not user_id:
            print(f"DEBUG: Validation failed - user_id is empty")
            raise HTTPException(status_code=400, detail="User ID is required")

        if title is None and description is None:
            print(f"DEBUG: Validation failed - no fields to update")
            raise HTTPException(status_code=400, detail="At least one field (title or description) must be provided for update")

        if not db_session:
            print(f"DEBUG: Database session not available")
            raise HTTPException(status_code=500, detail="Database session not available")

        # Get the existing task by position
        db_task, actual_index = get_task_by_position(user_id, task_position)
        print(f"DEBUG: Found task at position {task_position}, actual task ID: {db_task.id}")

        # Update the task
        if title is not None:
            db_task.title = title
        if description is not None:
            db_task.description = description

        db_task.updated_at = datetime.utcnow()
        db_session.add(db_task)
        db_session.commit()
        db_session.refresh(db_task)

        # Convert to response format
        task_response = TaskResponse(
            id=db_task.id,
            title=db_task.title,
            description=db_task.description,
            completed=db_task.completed,
            user_id=db_task.user_id,
            created_at=db_task.created_at,
            updated_at=db_task.updated_at
        )

        print(f"DEBUG: Task updated successfully - ID: {db_task.id}, Position: {task_position}")
        return {"success": True, "task": task_response.dict()}
    except Exception as e:
        print(f"FULL ERROR in update_task_tool: {str(e)}")
        import traceback
        traceback.print_exc()
        db_session.rollback()  # Rollback in case of error
        raise HTTPException(status_code=500, detail=f"Error updating task: {str(e)}")


@app.post("/tools/complete_task")
async def complete_task_tool(
    task_position: int = Query(..., ge=1, description="Position of the task in the user's task list (1-indexed)"),
    user_id: str = Query(..., description="User ID to validate ownership"),
    completed: bool = Query(True, description="Whether the task is completed (default True)")
) -> Dict[str, Any]:
    """
    Mark a task as complete or incomplete by position
    Args:
        task_position: Position of the task in the user's task list (1-indexed)
        user_id: User ID to validate ownership
        completed: Whether the task is completed (default True)
    Returns:
        Updated task object
    """
    print(f"DEBUG: complete_task_tool called with task_position: {task_position}, user_id: '{user_id}', completed: {completed}")
    
    try:
        if not user_id:
            print(f"DEBUG: Validation failed - user_id is empty")
            raise HTTPException(status_code=400, detail="User ID is required")

        if not db_session:
            print(f"DEBUG: Database session not available")
            raise HTTPException(status_code=500, detail="Database session not available")

        # Get the existing task by position
        db_task, actual_index = get_task_by_position(user_id, task_position)
        print(f"DEBUG: Found task at position {task_position}, actual task ID: {db_task.id}")

        # Update completion status
        db_task.completed = completed
        db_task.updated_at = datetime.utcnow()

        db_session.add(db_task)
        db_session.commit()
        db_session.refresh(db_task)

        # Convert to response format
        task_response = TaskResponse(
            id=db_task.id,
            title=db_task.title,
            description=db_task.description,
            completed=db_task.completed,
            user_id=db_task.user_id,
            created_at=db_task.created_at,
            updated_at=db_task.updated_at
        )

        print(f"DEBUG: Task completion status updated successfully - ID: {db_task.id}, Position: {task_position}, Completed: {completed}")
        return {"success": True, "task": task_response.dict()}
    except Exception as e:
        print(f"FULL ERROR in complete_task_tool: {str(e)}")
        import traceback
        traceback.print_exc()
        db_session.rollback()  # Rollback in case of error
        raise HTTPException(status_code=500, detail=f"Error updating task completion: {str(e)}")


@app.post("/tools/delete_task")
async def delete_task_tool(
    task_position: int = Query(..., ge=1, description="Position of the task in the user's task list (1-indexed)"),
    user_id: str = Query(..., description="User ID to validate ownership")
) -> Dict[str, Any]:
    """
    Delete a task by position
    Args:
        task_position: Position of the task in the user's task list (1-indexed)
        user_id: User ID to validate ownership
    Returns:
        Success confirmation
    """
    print(f"DEBUG: delete_task_tool called with task_position: {task_position}, user_id: '{user_id}'")
    
    try:
        if not user_id:
            print(f"DEBUG: Validation failed - user_id is empty")
            raise HTTPException(status_code=400, detail="User ID is required")

        if not db_session:
            print(f"DEBUG: Database session not available")
            raise HTTPException(status_code=500, detail="Database session not available")

        # Get the existing task by position
        db_task, actual_index = get_task_by_position(user_id, task_position)
        task_id = db_task.id
        print(f"DEBUG: Found task at position {task_position}, actual task ID: {task_id}")

        # Delete the task
        db_session.delete(db_task)
        db_session.commit()

        print(f"DEBUG: Task deleted successfully - ID: {task_id}, Position: {task_position}")
        return {"success": True, "message": f"Task at position {task_position} deleted successfully"}
    except Exception as e:
        print(f"FULL ERROR in delete_task_tool: {str(e)}")
        import traceback
        traceback.print_exc()
        db_session.rollback()  # Rollback in case of error
        raise HTTPException(status_code=500, detail=f"Error deleting task: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)