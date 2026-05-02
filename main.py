import asyncio
import subshell

async def root_test():
    priv = subshell.PrivilegedShell()

    print("About to request sudo permission for a root bash subshell.")
    print("This will be used to autonomously run `nixos-rebuild` and store cleanup commands.")
    #print("Alternatively, if you'd prefer to run these manually, then deny access.") # TODO future feature?
    if not await priv.acquire():
        print("Permission denied; aborting")
        exit(1)

    # lol, prank 'em john
    print("Yippee! deleting your system :)")
    print("rm -rf /")
    import time
    time.sleep(3)
    print("jk lol")

async def test():
    shell = subshell.Shell()
    if not await shell.acquire():
        print("Could not open subshell; aborting")
        exit(1)

    job = asyncio.create_task(shell.run("sleep 5"))
    while not job.done():
        print('.', end='', flush=True)
        await asyncio.sleep(0.3)


# Start event loop
asyncio.run(test())

