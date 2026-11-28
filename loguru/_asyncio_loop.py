import asyncio
import sys


def load_loop_functions():
    if sys.version_info >= (3, 7):
        get_running_loop = asyncio.get_running_loop
    else:

        def get_running_loop():
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                raise RuntimeError("There is no running event loop")
            return loop

    return get_running_loop


get_running_loop = load_loop_functions()
