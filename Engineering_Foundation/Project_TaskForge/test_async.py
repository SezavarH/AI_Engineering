import asyncio
from uuid import uuid4
from services import TaskService
from models import TaskPriority

async def main():
    service = TaskService()

    # Create some tasks
    task_ids = []
    for i in range(10):
        task = service.create_task(
            project_id=uuid4(),
            title=f"Task {i+1}",
            description=f"Description for task {i+1}",
            priority=TaskPriority.MEDIUM,
        )
        task_ids.append(task.id)

    # Process tasks concurrently with a limit of 3 concurrent tasks
    processed_tasks = await service.process_tasks(task_ids, max_concurrent=3)

    # Print the results
    for task in processed_tasks:
        print(f"Task ID: {task.id}, Status: {task.status}, Started At: {task.started_at}, Completed At: {task.completed_at}")

if __name__ == "__main__":
    asyncio.run(main())