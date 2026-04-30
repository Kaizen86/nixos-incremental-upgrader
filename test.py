
import subprocess
import os

def Popen_piped(cmd: list):
    return subprocess.Popen(cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

acquire = Popen_piped(["sudo","whoami"])
out, _ = acquire.communicate() # Let user enter the password
out = out.strip()
if out != b'root':
    print("Failed to acquire root shell")
    exit(1)
del acquire, out

# At this point, sudo should cache the password
priv = Popen_piped(["sudo","bash"])
# Disable blocking (UNIX only)
os.set_blocking(priv.stdout.fileno(), False)
os.set_blocking(priv.stderr.fileno(), False)

def priv_run(*cmds: list) -> tuple:
    cmd = ' && '.join(cmds)
    cmd = f"({cmd}); echo DONE:$?\n"
    print(cmd)
    priv.stdin.write(cmd.encode('utf-8'))
    stdout_culm = stderr_culm  = ""

    while True:
        stdout = priv.stdout.readline().decode()
        stderr = priv.stderr.readline().decode()
        stdout_culm += stdout
        stderr_culm += stderr
        if "DONE" in stdout:
            break
    return stdout, stderr

print(priv_run("whoami"))

# Must make sure to close the subshell!
priv.terminate()
priv.wait()

