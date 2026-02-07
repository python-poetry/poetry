# Test script to reproduce issue #10703 in poetry
# Expected: poetry remove pylint should succeed
from poetry.factory import Factory
from poetry.project.project import Project

# Simulated project setup
project = Project('test_project')
poetry = Factory().create_poetry(project)
poetry.add_dependency('pylint', {'optional': True})
poetry.remove_dependency('pylint')
print("Optional dependency removed successfully.")