import asyncio
import os
import selectors
import subprocess

def Popen_piped(cmd: list):
    return subprocess.Popen(cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0)


class Shell():
    def __init__(self, shell="bash", pollrate=0.1):
        self.shell = shell
        self.pollrate = pollrate
        self._acquired = False

    async def acquire(self):
        """Opens the subshell.
        This must be called before any commands can be run.
        Returns True when successful."""
        self._proc = proc = Popen_piped([self.shell])
        self._acquired = True

        code, *_ = await self.run("whoami")
        return code == 0

    async def run(self, *cmds: list) -> tuple:
        """Executes one or more shell commands.
        Permission must first be sought using .acquire()

        Important note: it is the caller's responsibility to escape commands, otherwise the underlying shell may get stuck waiting for extra input.
        For example: `echo '` should be escaped as: `"echo \\'"` or `r"echo \'"`

        If they should be chained, provide them as separate arguments.
        For instance, `await shell.run("mkdir foo", "touch foo/a")` is equivalent to `mkdir foo && touch foo/a`

        If the commands are not dependent on each other, they should be run separately to avoid collateral damage.
        For instance, `await shell.run("touch a"); await shell.run("touch b")` is equivalent to `touch a; touch b`

        If your commands should be run in parallel, consider creating multiple privileged shells.
        """
        if not self._acquired:
            raise Exception("Shell not acquired")

        # Grade-A jank ahead!!

        cmd = ' && '.join(cmds)
        cmd = f"(true;{cmd}); echo DONE:$?; echo DONE >&2\n"
        self._proc.stdin.write(cmd.encode('utf-8'))

        def stream_reader(stream):
            lines = list()
            # Set up a way to check if the stream has data
            sel = selectors.DefaultSelector()
            sel.register(stream, selectors.EVENT_READ)

            while True:
                if not sel.select(timeout=0):
                    yield None

                line = stream.readline().decode()
                lines.append(line.strip('\n'))

                if "DONE" in line:
                    yield lines
                    return

        # Create stream readers
        stdout_reader = stream_reader(self._proc.stdout)
        stderr_reader = stream_reader(self._proc.stderr)
        # Try reading command output
        stdout = next(stdout_reader)
        stderr = next(stderr_reader)

        # Keep reading until both streams are done
        while stdout == None or stderr == None:
            await asyncio.sleep(0.01)

            if stdout == None:
                stdout = next(stdout_reader)

            if stderr == None:
                stderr = next(stderr_reader)

        # Tidy up and extract exit code
        *stdout, stdout_exit = stdout
        exit_code = stdout_exit.removeprefix('DONE:')
        *stderr, _ = stderr

        return int(exit_code), stdout, stderr

    def __bool__(self):
        return self._acquired

    def __del__(self):
        if not self._acquired:
            return
        # Must make sure to close the subshell!
        self._proc.terminate()
        self._proc.wait()


class PrivilegedShell(Shell):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def acquire(self):
        """Requests root shell access from the user via sudo.
        This must be called before any commands can be run, and is dependent on the user granting sudo permission.
        Returns True when successful."""
        with Popen_piped(["sudo", "whoami"]) as acquire:
            out, _ = acquire.communicate() # Let user enter the password
            if out.strip() != b'root':
                return False

        # At this point, sudo should cache the password
        self._proc = proc = Popen_piped(["sudo", self.shell])
        self._acquired = True

        code, *_ = await self.run("whoami")
        return code == 0


async def example():
    priv = PrivilegedShell()
    if not await priv.acquire():
        print("Failed to acquire root shell")
        exit(1)

    # Prove that `whoami` will return 'root' in stdout
    assert (await priv.run("whoami")) == (0, ['root'], [])

    # Chained command examples
    assert (await priv.run("echo a", "echo b")) == (0, ['a','b'], [])
    # Note: always take care to escape strings!
    assert (await priv.run("false", r"echo This won\'t run")) == (1, [], [])

    # Example of how to catch errors
    exit_code, stdout, stderr = await priv.run("bad-command")
    if exit_code != 0:
        print("Example error catching:")
        print('\n'.join(stderr))
    else:
        print("Command okay(?!)")

if __name__ == "__main__":
    asyncio.run(example())

