import asyncio
import root_subshell

async def main():
    priv = root_subshell.PrivilegedShell()

    print("About to request sudo permission for a root bash subshell.")
    print("This will be used to autonomously run `nixos-rebuild` and store cleanup commands.")
    if not await priv.acquire():
        print("Permission denied; aborting")
        exit(1)

    # lol, prank 'em john
    print("Yippee! deleting your system :)")
    print("rm -rf /")
    import time
    time.sleep(3)
    print("jk lol")


# Start event loop
asyncio.run(main())

