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

class PrivilegedShell():
    def __init__(self):
        self._acquired = False

    async def acquire(self):
        with Popen_piped(["sudo", "whoami"]) as acquire:
            out, _ = acquire.communicate() # Let user enter the password
            if out.strip() != b'root':
                return False

        # At this point, sudo should cache the password
        self._proc = proc = Popen_piped(["sudo", "bash"])
        self._acquired = True

        code, *_ = await self.run("whoami")
        return code == 0

    async def run(self, *cmds: list) -> tuple:
        if not self._acquired:
            raise Exception("Not acquired")

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
                lines.append(line.strip())

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

    def __del__(self):
        if not self._acquired:
            return
        # Must make sure to close the subshell!
        self._proc.terminate()
        self._proc.wait()

async def example():
    priv = PrivilegedShell()
    if not await priv.acquire():
        print("Failed to acquire root shell")
        exit(1)

    print(await priv.run("whoami"))
    print(await priv.run("nixos-rebuild switch"))


if __name__ == "__main__":
    asyncio.run(example())

