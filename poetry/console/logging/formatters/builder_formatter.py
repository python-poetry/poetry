import re

from .formatter import Formatter


class BuilderLogFormatter(Formatter):
    def format(self, msg):  # type: (str) -> str
        if msg.startswith(" - Building ") or msg.startswith(" - Built "):
            msg = re.sub(r" - (Buil(?:t|ing)) (.+)", " - \\1 <c2>\\2</c2>", msg)
        elif msg.startswith(" - Adding: "):
            msg = re.sub(r" - Adding: (.+)", " - Adding: <b>\\1</b>", msg)

        return msg
