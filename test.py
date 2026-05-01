import time
import subprocess
import selectors
import os

def Popen_piped(cmd: list):
    return subprocess.Popen(cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0)

with Popen_piped(["sudo", "whoami"]) as acquire:
    out, _ = acquire.communicate() # Let user enter the password
    if out.strip() != b'root':
        print("Failed to acquire root shell")
        exit(1)

# At this point, sudo should cache the password
priv = Popen_piped(["sudo", "bash"])
# Set up a way to check if the output streams have data
priv_stdout_sel = selectors.DefaultSelector()
priv_stdout_sel.register(priv.stdout, selectors.EVENT_READ)
priv_stderr_sel = selectors.DefaultSelector()
priv_stderr_sel.register(priv.stderr, selectors.EVENT_READ)

def priv_run(*cmds: list) -> tuple:
    cmd = ' && '.join(cmds)
    cmd = f"({cmd}); echo DONE:$?\n"
    priv.stdin.write(cmd.encode('utf-8'))
    stdout_culm = stderr_culm = ""

    while True:
        if priv_stderr_sel.select(timeout=0):
            stderr = priv.stderr.readline().decode()
            stderr_culm += stderr

        if priv_stdout_sel.select(timeout=0):
            stdout = priv.stdout.readline().decode()
            stdout_culm += stdout
            if "DONE" in stdout:
                break
        time.sleep(0.01)

    return stdout_culm, stderr_culm

print(priv_run("whoami"))

# Must make sure to close the subshell!
priv.terminate()
priv.wait()

