from dpyConsole import Console, Cog
from dpyConsole import console


class ConsoleListener(Cog):

    def __init__(self, console_: Console):
        self.console = console_

    @console.command()
    async def test(self):
        print("Hey")


def setup(con: Console):
    con.add_console_cog(ConsoleListener(con))
