from PIL import Image
import os

def interpolate_frames(img1, img2, num_interpolated_frames):
    """Generate interpolated frames between two images."""
    frames = []

    for t in range(num_interpolated_frames + 1):
        alpha = t / (num_interpolated_frames + 1)  # Normalized interpolation factor
        interpolated_frame = Image.blend(img1, img2, alpha)
        frames.append(interpolated_frame)

    return frames


def create_gif(frame_folder, output_path, fps=60, frame_prefix="frame_", frame_extension=".png",
               num_interpolated_frames=2):
    frames = []
    duration = int(1000 / fps)  # Duration per frame in milliseconds for the specified FPS

    # Calculate the total number of frames by counting matching files in the directory
    num_frames = len(
        [name for name in os.listdir(frame_folder) if name.startswith(frame_prefix) and name.endswith(frame_extension)])

    # Load frames in sequential order based on the expected file naming convention
    for i in range(num_frames):
        frame_path = os.path.join(frame_folder, f"{frame_prefix}{i}{frame_extension}")
        img = Image.open(frame_path).convert("RGBA")  # Convert to RGBA for better quality

        if i > 0:
            # Interpolate frames between the previous and current frame
            interpolated_frames = interpolate_frames(frames[-1], img, num_interpolated_frames)
            frames.extend(interpolated_frames)

        frames.append(img)

    if frames:
        # Convert each frame to RGB before quantization
        frames = [frame.convert("RGB").quantize(method=Image.MEDIANCUT) for frame in frames]

        # Save frames as a GIF with higher quality settings
        frames[0].save(output_path, format='GIF', append_images=frames[1:],
                       save_all=True, duration=duration, loop=0, dither=Image.NONE)  # Dither can be adjusted
        #print(f"GIF created successfully with {len(frames)} frames at {output_path}")
    else:
        print("No frames found in the specified folder.")


##############################################################


# Usage example
#frame_folder = 'frames'
#output_path = 'output/output.gif'
#create_gif(frame_folder, output_path, fps=24, num_interpolated_frames=0)  # duration in fps
