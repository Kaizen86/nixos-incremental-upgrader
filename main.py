import subprocess
import os

password = (input("sudo password:")+'\n').encode('utf8')

env = os.environ.copy()
env['SUDO_ASKPASS'] = 'cat'
priv = subprocess.Popen(["sudo","-A","bash"],
    env=env,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE)


out, err = priv.communicate(input=password)
print(out, err)
