import subprocess
import asyncio
import os

async def run_js_script(script_path, *args):
    # Prepare the command with arguments
    command = ["node", script_path] + list(args)

    # Start the subprocess
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Read the output and error streams
    stdout, stderr = await process.communicate()

    # Decode the output and error to strings
    stdout = stdout.decode().strip()
    stderr = stderr.decode().strip()

    return stdout, stderr


async def call_js_script(script_path, args=("", "")):

    # Run the script
    stdout, stderr = await run_js_script(script_path, *args)

    # Print the output and errors
    print("JavaScript output:", stdout)
    if stderr:
        print("JavaScript errors:", stderr)


# Run the main function
if __name__ == "__main__":
    dir_path = os.path.dirname(os.path.realpath(__file__))
    asyncio.run(call_js_script(script_path=r"C:/Users/Server/Desktop/dimensionbot-2.0/capture-svg-frames.js", args=(r"C:/Users/Server/Desktop/dimensionbot-2.0/downloaded_svgs/embedded_svg_1.svg", '')))
