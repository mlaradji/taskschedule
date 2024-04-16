from typing import Optional, Sequence, Dict, List
from taskschedule.tasklib3.sqlpydantic import (
    pydantic_column_type,
    CommaSeparatedList,
    Epoch,
)
from taskschedule.tasklib3.exceptions import TaskWarriorException
from sqlmodel import Field, Session, SQLModel, create_engine, select, Column
from uuid import UUID, uuid4
from enum import Enum
from pathlib import Path
from frozendict import frozendict, deepfreeze

from loguru import logger
from functools import cached_property
import re
import subprocess
import os


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


CONFIG_REGEX = re.compile(r"^(?P<key>[^\s]+)\s+(?P<value>[^\s].*$)")

ConfigOption = str | int
Overrides = Dict[str, str | int]


class TaskWarrior:
    tasks: Sequence[Task]
    task_command: str
    taskrc_location: Optional[Path]
    overrides: Overrides

    def __init__(
        self,
        data_location: Path,
        taskrc_location: Optional[Path] = None,
        filter_obj=True,
        task_command: str = "task",
    ):
        self.task_command = task_command
        self.overrides = {
            "confirmation": "no",
            "dependency.confirmation": "no",  # See TW-1483 or taskrc man page
            "recurrence.confirmation": "no",  # Necessary for modifying R tasks
            # Defaults to on since 2.4.5, we expect off during parsing
            "json.array": "off",
            # 2.4.3 onwards supports 0 as infite bulk, otherwise set just
            # arbitrary big number which is likely to be large enough
            "bulk": 0,
        }

        self.taskrc_location = taskrc_location
        self.engine = create_engine(f"sqlite:///{data_location}/taskchampion.sqlite3")
        with Session(self.engine) as session:
            statement = select(Task).where(filter_obj)
            self.tasks = session.exec(statement).all()

    @cached_property
    def config(self) -> frozendict[str, ConfigOption]:
        # If not, fetch the config using the 'show' command
        raw_output = self.execute_command(
            ["show"], config_override={"verbose": "nothing"}
        )

        config: Dict[str, str] = dict()

        footer = raw_output.pop()
        if footer == "Some of your .taskrc variables differ from the default values.":
            logger.debug(footer)
        else:
            raw_output.append(footer)

        for line in raw_output[3:]:  # skip header
            match = CONFIG_REGEX.match(line)
            if match:
                key = match.group("key")
                value = match.group("value").strip()
                config[key] = value

        return deepfreeze(config)

    def _get_task_command(self) -> List[str]:
        return self.task_command.split()

    def _get_command_args(
        self, args: Sequence[str | bytes], config_override: Optional[Overrides] = None
    ) -> List[str]:
        command_args = self._get_task_command()

        if config_override is not None:
            overrides = self.overrides.copy()
            overrides.update(config_override or dict())
        for item in overrides.items():
            command_args.append("rc.{0}={1}".format(*item))
        command_args.extend(
            [x.decode("utf-8") if isinstance(x, bytes) else str(x) for x in args]
        )
        return command_args

    def execute_command(
        self,
        args: Sequence[str],
        config_override: Optional[Overrides] = None,
        allow_failure: bool = True,
        return_all: bool = False,
    ) -> List[str]:
        command_args = self._get_command_args(args, config_override=config_override)

        logger.debug("Executing `task` command...", command_args=" ".join(command_args))

        env = os.environ.copy()
        if self.taskrc_location:
            env["TASKRC"] = str(self.taskrc_location)
        p = subprocess.Popen(
            command_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
        )
        stdout, stderr = [x.decode("utf-8") for x in p.communicate()]
        if p.returncode and allow_failure:
            if stderr.strip():
                error_msg = stderr.strip()
            else:
                error_msg = stdout.strip()
            error_msg += "\nCommand used: " + " ".join(command_args)
            raise TaskWarriorException(error_msg)

        logger.debug(
            "`task` command executed.",
            stdout=stdout.rstrip(),
            stderror=stderr.rstrip(),
            status=p.returncode,
        )

        return stdout.rstrip().split("\n")


if __name__ == "__main__":
    tw = TaskWarrior(Path("/home/mohamed/.local/share/task"))
    print(tw.tasks[0].data)
    print(tw.config)
