from uuid import UUID
from typing import Optional
from datetime import datetime, timezone

from .models import Task, TaskPriority, TaskStatus
import asyncio
import random

class TaskService:
    def __init__(self) -> None:
        self._tasks: dict[UUID, Task] = {}

    def create_task(
        self,
        project_id: UUID,
        title: str,
        description: str,
        priority: TaskPriority,
        assignee_id: Optional[UUID] = None,
    ) -> Task:
        task = Task(
            project_id=project_id,
            title=title,
            description=description,
            status=TaskStatus.TODO,
            priority=priority,
            assignee_id=assignee_id,
        )
        self._tasks[task.id] = task
        return task

    def get_task(self, task_id: UUID) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list_tasks(self, project_id: Optional[UUID] = None) -> list[Task]:
        if project_id:
            return [task for task in self._tasks.values() if task.project_id == project_id]
        return list(self._tasks.values())

    def start_task(self, task_id: UUID) -> Task:
        task = self.get_task(task_id)
        if not task:
            raise ValueError("Task not found.")
        if task.status != TaskStatus.TODO:
            raise ValueError("Only tasks in 'To Do' status can be started.")
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now(timezone.utc)
        return task

    def complete_task(self, task_id: UUID) -> Task:
        task = self.get_task(task_id)
        if not task:
            raise ValueError("Task not found.")
        if task.status != TaskStatus.IN_PROGRESS:
            raise ValueError("Only tasks in 'In Progress' status can be completed.")
        task.status = TaskStatus.DONE
        task.completed_at = datetime.now(timezone.utc)
        return task

    # async 
    async def process_tasks(self, task_ids: list[UUID], max_concurrent: int = 3) -> list[Task]:
        semaphore = asyncio.Semaphore(max_concurrent)

        # call start_task and complete_task for each task_id
        async def process_single_task(task_id: UUID) -> Task:
            async with semaphore: 
                self.start_task(task_id)
                await asyncio.sleep(random.uniform(0.1, 0.5))  # Simulate some processing time
                return self.complete_task(task_id)

        return await asyncio.gather(*(process_single_task(tid) for tid in task_ids))
    
