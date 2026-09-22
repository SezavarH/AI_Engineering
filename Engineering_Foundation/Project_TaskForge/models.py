from pydantic import BaseModel, Field, model_validator
from typing import Optional
import uuid
from datetime import datetime, timezone
from enum import Enum


class TaskStatus(str, Enum):                                        # str can accepts any string value, Enum restricts it to the defined values
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    DONE = "Done"

class TaskPriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"



class User(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)               # Unique identifier for the user
    email: str
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))                                      

class Project(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    owner_id: uuid.UUID                                             # Foreign-key fields must not have defaults
    created_at: datetime  = Field(default_factory=lambda: datetime.now(timezone.utc))

class Task(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID                                           # Foreign-key fields must not have defaults
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assignee_id: Optional[uuid.UUID] = None
    created_at: datetime  = Field(default_factory=lambda: datetime.now(timezone.utc))  # Timestamp when the task was created
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def is_open(self) -> bool:
        return self.status in {TaskStatus.TODO, TaskStatus.IN_PROGRESS}

    @property
    def duration(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @model_validator(mode="after")
    def check_completion_status(self) -> 'Task':
        if self.status == TaskStatus.DONE and self.completed_at is None:
            raise ValueError("Completed tasks must have a completed_at timestamp.")
        return self
