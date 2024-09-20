from taskschedule.tasklib3.backends import TaskWarrior


def test_import():
    tw = TaskWarrior("./test_data", taskrc_location="./test_data/taskrc")
