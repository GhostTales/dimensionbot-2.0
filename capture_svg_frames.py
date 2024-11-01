import subprocess
import os

def capture_svg_frames(url, output_dir="frames"):
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Call the JavaScript file
    process = subprocess.run(["node", "captureFrames.js", url, output_dir],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Check for errors
    if process.returncode != 0:
        print("Error:", process.stderr)
    else:
       # print("Frames captured and saved to:", output_dir)
        return


##############################################################
# Example usage
#link = "https://osu-sig.vercel.app/card?user=Ghost-Tales&mode=std&lang=en&blur=1&round_avatar=true&animation=true&hue=218&w=1100&h=640"
#capture_svg_frames(url=link, output_dir="frames")
