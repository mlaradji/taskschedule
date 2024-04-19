from typing import Optional
from taskschedule.tasklib3.sqlpydantic import (
    pydantic_column_type,
    CommaSeparatedList,
    Epoch,
)
from sqlmodel import Field, SQLModel, Column
from uuid import UUID, uuid4
from enum import Enum


class Status(str, Enum):
    Pending = "pending"
    Completed = "completed"
    Deleted = "deleted"
    Recurring = "recurring"
    Waiting = "waiting"


class Priority(str, Enum):
    L = "L"
    M = "M"
    H = "H"


class TaskData(SQLModel, table=False):  # type: ignore[call-arg]
    entry: Optional[Epoch] = None
    start: Optional[Epoch] = None
    end: Optional[Epoch] = None
    modified: Optional[Epoch] = None
    scheduled: Optional[Epoch] = None
    recur: Optional[str] = None
    mask: Optional[str] = None
    imask: Optional[str] = None
    parent: Optional[UUID] = None
    wait: Optional[Epoch] = None
    due: Optional[Epoch] = None
    until: Optional[Epoch] = None
    status: Status = Status.Pending
    description: str = Field(default_factory=str)
    priority: Optional[Priority] = None
    project: Optional[str] = None
    tags: CommaSeparatedList = Field(default_factory=list)
    depends: CommaSeparatedList = Field(default_factory=list)
    annotations: Optional[str] = None


class Task(SQLModel, table=True):  # type: ignore[call-arg]
    __tablename__: str = "tasks"  # type: ignore[misc]
    uuid: UUID = Field(default_factory=uuid4, primary_key=True)
    data: TaskData = Field(
        default_factory=TaskData, sa_column=Column(pydantic_column_type(TaskData))
    )
