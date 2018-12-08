from clikit.api.args import Args
from clikit.api.args import RawArgs
from clikit.api.args.format import ArgsFormat
from clikit.api.args.format import ArgsFormatBuilder
from clikit.args import DefaultArgsParser


class RunArgsParser(DefaultArgsParser):
    """
    Parser that just parses command names and leave the rest
    alone to be passed to the command.
    """

    def parse(
        self, args, fmt, lenient=False
    ):  # type: (RawArgs, ArgsFormat, bool) -> Args
        builder = ArgsFormatBuilder()
        builder.set_command_names(*fmt.get_command_names())
        builder.set_arguments(*fmt.get_arguments().values())
        fmt = builder.format

        return super(RunArgsParser, self).parse(args, fmt, True)

    def _parse(
        self, raw_args, fmt, lenient
    ):  # type: (RawArgs, ArgsFormat, bool) -> None
        """
        Parse everything as a single, multi-valued argument.
        """
        tokens = raw_args.tokens[:]

        last_arg = list(fmt.get_arguments().values())[-1]
        self._arguments[last_arg.name] = []

        while True:
            try:
                token = tokens.pop(0)
            except IndexError:
                break

            self._arguments[last_arg.name].append(token)
