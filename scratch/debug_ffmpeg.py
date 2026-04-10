import subprocess
from pathlib import Path

def test_ffmpeg():
    # Test a simple zoompan + hardware encoder to see if it fails on this system
    # We will use a dummy image (black)
    img_path = Path("test_black.png")
    from PIL import Image
    Image.new("RGB", (1920, 1080), (0,0,0)).save(img_path)
    
    # Try one pass style for ONE frame
    cmd = [
        "ffmpeg", "-loop", "1", "-t", "2", "-i", str(img_path),
        "-filter_complex", "[0:v]scale=2150:1209,zoompan=z=1.1:d=60:s=1920x1080:fps=30[v0]",
        "-map", "[v0]", "-c:v", "libx264", "-preset", "ultrafast", "test_out.mp4", "-y"
    ]
    
    print("Testing FFmpeg Command...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FAILED!")
        print("STDOUT:", r.stdout)
        print("STDERR:", r.stderr)
    else:
        print("SUCCESS!")

    # Now test with drive letter handling for ASS filter if possible
    # (Just simulate the path)
    ass_path = r"D:\ATHARV\W\ITG\CODE\shorts\youtube-shorts-pipeline\captions.ass"
    safe_ass_path = str(ass_path).replace("\\", "/").replace(":", "\\:")
    print(f"DEBUG: safe_ass_path is {safe_ass_path}")

if __name__ == "__main__":
    test_ffmpeg()
