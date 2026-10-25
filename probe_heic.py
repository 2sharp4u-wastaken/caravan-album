import sys, subprocess, glob, os, traceback, platform
root = os.path.abspath("..")
log = open("probe.txt", "w", encoding="utf-8")
def P(*a):
    s = " ".join(str(x) for x in a); print(s); log.write(s + "\n"); log.flush()
P("python", sys.version, platform.platform())
heics = sorted(glob.glob(os.path.join(root, "*.heic")))[:3]
P("sample heic:", heics)
# 1) does PyAV decode HEIC?
try:
    import av
    for h in heics[:2]:
        try:
            with av.open(h) as c:
                fr = next(c.decode(video=0))
                P("PyAV OK", os.path.basename(h), fr.width, fr.height, c.format.name)
        except Exception as e:
            P("PyAV FAIL", os.path.basename(h), type(e).__name__, e)
except Exception as e:
    P("av import fail", e)
# 2) try several pillow-heif versions
py = sys.executable
for ver in ["0.22.0", "0.21.0", "1.0.0", "1.1.1", "0.20.0", "0.18.0"]:
    r = subprocess.run([py, "-m", "pip", "install", "-q", "--disable-pip-version-check", "--force-reinstall", "--no-deps", "pillow-heif==" + ver], capture_output=True, text=True)
    if r.returncode:
        P("pip", ver, "install failed:", r.stderr.strip()[-150:]); continue
    t = subprocess.run([py, "-c", "import pillow_heif; from PIL import Image; pillow_heif.register_heif_opener(); import sys; im=Image.open(sys.argv[1]); im.load(); print(im.size)", heics[0] if heics else ""], capture_output=True, text=True)
    P("pillow-heif", ver, "->", "OK " + t.stdout.strip() if t.returncode == 0 else "BLOCKED/FAIL " + t.stderr.strip()[-160:])
    if t.returncode == 0:
        P("WORKING VERSION", ver); break
# 3) Windows WIC HEIF codec present?
ps = ("Add-Type -AssemblyName PresentationCore; $s=[IO.File]::OpenRead('%s'); try{$d=[Windows.Media.Imaging.BitmapDecoder]::Create($s,'None','OnLoad'); 'WIC OK '+$d.Frames[0].PixelWidth+'x'+$d.Frames[0].PixelHeight}catch{'WIC FAIL '+$_.Exception.Message}" % (heics[0].replace("'", "''") if heics else ""))
r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
P("WIC:", (r.stdout + r.stderr).strip()[:200])
P("probe done")
