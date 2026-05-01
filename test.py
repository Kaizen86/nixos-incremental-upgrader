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
        # Set up a way to check if the output streams have data
        self._stdout_sel = selectors.DefaultSelector()
        self._stdout_sel.register(proc.stdout, selectors.EVENT_READ)
        self._stderr_sel = selectors.DefaultSelector()
        self._stderr_sel.register(proc.stderr, selectors.EVENT_READ)

        code, *_ = await self.run("whoami")
        return code == 0

    async def run(self, *cmds: list) -> tuple:
        if not self._acquired:
            raise Exception("Not acquired")

        cmd = ' && '.join(cmds)
        cmd = f"(true;{cmd}); echo DONE:$?\n"
        self._proc.stdin.write(cmd.encode('utf-8'))

        stdout_culm = stderr_culm = ""
        while True:
            if self._stderr_sel.select(timeout=0):
                stderr_chunk = self._proc.stderr.readline().decode()
                stderr_culm += stderr_chunk

            if self._stdout_sel.select(timeout=0):
                stdout_chunk = self._proc.stdout.readline().decode()
                stdout_culm += stdout_chunk
                if "DONE:" in stdout_chunk:
                    break
            asyncio.sleep(0.01)

        stdout_culm = stdout_culm.split('\n')[:-1]
        stderr_culm = stderr_culm.split('\n')[:-1]

        # Extract exit code
        *stdout_culm, exit_line = stdout_culm
        exit_code = exit_line.removeprefix('DONE:')

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

