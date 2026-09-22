from fastapi import FastAPI, Depends, status, HTTPException
from services import TaskService
from pydantic import BaseModel
from uuid import UUID
from models import TaskPriority
from typing import Optional
from functools import lru_cache

app = FastAPI()

class CreateTaskRequest(BaseModel):
    project_id: UUID
    title: str
    description: str
    priority: TaskPriority
    assignee_id: Optional[UUID] = None




@lru_cache                                                                      # Cache the TaskService instance to avoid creating a new one for each request
def get_task_service() -> TaskService:
    return TaskService()

@app.post("/tasks/", status_code=status.HTTP_201_CREATED)
def create_task(payload: CreateTaskRequest, service = Depends(get_task_service)):
    task = service.create_task(
        project_id=payload.project_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        assignee_id=payload.assignee_id
    )
    return task

@app.get("/tasks/{task_id}", status_code=status.HTTP_200_OK)
def get_task(task_id: UUID, service = Depends(get_task_service)):
    task = service.get_task(task_id)
    if not task:
        return HTTPException(status_code=404, detail="Task not found.")
    return task

@app.get("/tasks/", status_code=status.HTTP_200_OK)
def list_tasks(project_id: Optional[UUID] = None, service = Depends(get_task_service)):
    tasks = service.list_tasks(project_id)
    return tasks

@app.post("/tasks/{task_id}/start", status_code=status.HTTP_200_OK)
def start_task(task_id: UUID, service = Depends(get_task_service)):
    task = service.start_task(task_id)
    if not task:
        return HTTPException(status_code=404, detail="Task not found.")
    return task

@app.post("/tasks/{task_id}/complete", status_code=status.HTTP_200_OK)
def complete_task(task_id: UUID, service = Depends(get_task_service)):
    task = service.complete_task(task_id)
    if not task:
        return HTTPException(status_code=404, detail="Task not found.")
    return task
