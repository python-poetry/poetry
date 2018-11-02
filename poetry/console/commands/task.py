from .env_command import EnvCommand


class TaskCommand(EnvCommand):
    """
    Runs a task in the appropriate environment.

    task
        { task : The task to run.}
    """

    def handle(self):
        task = self.argument("task")
        tasks = self.poetry.local_config.get("tasks")

        if tasks and task in tasks:
            return self.run_task(tasks[task])

    def run_task(self, task):
        return self.env.run(*task.split(), shell=True, call=True)
