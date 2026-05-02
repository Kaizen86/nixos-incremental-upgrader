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

        stdout = stream_reader(self._proc.stdout)
        stdout_culm = None
        stderr = stream_reader(self._proc.stderr)
        stderr_culm = None

        while stdout_culm == None or stderr_culm == None:
            if stdout_culm == None:
                stdout_culm = next(stdout)

            if stderr_culm == None:
                stderr_culm = next(stderr)

            await asyncio.sleep(0.01)

        # Tidy up and extract exit code
        *stdout_culm, stdout_exit = stdout_culm
        exit_code = stdout_exit.removeprefix('DONE:')
        *stderr_culm, _ = stderr_culm

        return int(exit_code), stdout_culm, stderr_culm

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

