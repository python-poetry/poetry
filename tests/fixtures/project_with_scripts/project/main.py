import sys


def relay(args=None):
    args = args or sys.argv[1:]
    print("entered relay")
    print(args)
    exit_code = args[0]
    return exit_code
