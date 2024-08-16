import asyncio
from PIL import Image
import aiofiles
import os
import io


async def load_image(file_path):
    async with aiofiles.open(file_path, 'rb') as f:
        file_content = await f.read()
    return Image.open(io.BytesIO(file_content))


async def create_gif_from_pngs(png_folder, output_gif, delay=100, loop_start=20, loop_end=35):
    # Ensure output directory exists
    output_dir = os.path.dirname(output_gif)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # List all PNG files and create full file paths
    png_files = [os.path.join(png_folder, f"frame_{i}.png") for i in range(1, 36)]

    # Load images asynchronously
    tasks = [load_image(file) for file in png_files]
    images = await asyncio.gather(*tasks)

    # Convert all images to the same mode (RGBA) and ensure they're all the same size
    images = [img.convert("RGBA") for img in images]

    # Repeat frames 10 to 25 to simulate looping
    loop_frames = images[loop_start - 1:loop_end]
    frames = images[:loop_start - 1] + loop_frames * 10  # Repeat loop_frames three times

    # Save the GIF with the looped frames
    frames[0].save(
        output_gif,
        save_all=True,
        append_images=frames[1:],
        duration=delay,
        loop=0  # Infinite loop
    )


if __name__ == "__main__":
    png_folder = "downloaded_svgs/frames/"
    output_gif = "downloaded_svgs/outputGif/output.gif"

    # Run the asynchronous function
    asyncio.run(create_gif_from_pngs(png_folder, output_gif))
