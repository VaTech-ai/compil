import hashlib
import os
import shutil
import subprocess
import tarfile
import urllib.request

WORK = "./temp"
EXPORT = "./output"
SRC_TAR = "opencv-5.1.0.tar.gz"
SRC_MD5 = "0cc6c9bd199223be79acd7a9a66bf896"
NDK_ZIP = "android-ndk-r25c-linux.zip"
SRC_URL = "https://github.com/opencv/opencv/archive/refs/tags/5.1.0.tar.gz"
NDK_URL = "https://dl.google.com/android/repository/android-ndk-r25c-linux.zip"
OUTPUT = "video-arm64.tar.gz"

def run(command):
    print("+ " + command, flush=True)
    subprocess.run(command, shell=True, check=True)

def md5_of(path):
    digest = hashlib.md5()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def fetch(url, target):
    if os.path.exists(target) and os.path.getsize(target) > 1024 * 1024:
        print("Déjà présent: " + target, flush=True)
        return
    print("Téléchargement " + url, flush=True)
    urllib.request.urlretrieve(url, target + ".part")
    os.replace(target + ".part", target)
    print(f"{target} -> {os.path.getsize(target) // (1024 * 1024)} Mo", flush=True)

os.makedirs(WORK, exist_ok=True)
os.chdir(WORK)
print(f"CPUs disponibles: {os.cpu_count()}", flush=True)

fetch(SRC_URL, SRC_TAR)
got = md5_of(SRC_TAR)
print("Sources MD5: " + got, flush=True)
if got != SRC_MD5:
    raise SystemExit(f"Sources inattendues: {got}")

fetch(NDK_URL, NDK_ZIP)

if not os.path.isdir("opencv-5.1.0"):
    run("tar -xzf " + SRC_TAR)
if not os.path.isdir("android-ndk-r25c"):
    run("unzip -q " + NDK_ZIP)

ndk = os.path.abspath("android-ndk-r25c")
build = os.path.abspath("build-arm64")
install = os.path.abspath("android-out")

flags = [
    "-DBUILD_LIST=video",
    "-DBUILD_opencv_video=ON",
    "-DBUILD_SHARED_LIBS=OFF",
    "-DBUILD_TESTS=OFF",
    "-DBUILD_PERF_TESTS=OFF",
    "-DBUILD_EXAMPLES=OFF",
    "-DBUILD_opencv_apps=OFF",
    "-DBUILD_opencv_python3=OFF",
    "-DBUILD_JAVA=OFF",
    "-DBUILD_ANDROID_PROJECTS=OFF",
    "-DBUILD_ANDROID_EXAMPLES=OFF",
    "-DBUILD_opencv_ts=OFF",
    "-DBUILD_PROTOBUF=OFF",
    "-DWITH_PROTOBUF=OFF",
    "-DWITH_OPENCL=OFF",
    "-DWITH_IPP=OFF",
    "-DWITH_TBB=OFF",
    "-DWITH_OPENMP=OFF",
    "-DWITH_PTHREADS_PF=OFF",
    "-DWITH_ITT=OFF",
    "-DWITH_EIGEN=OFF",
    "-DWITH_LAPACK=OFF",
    "-DWITH_FFMPEG=OFF",
    "-DWITH_GSTREAMER=OFF",
    "-DWITH_JPEG=OFF",
    "-DWITH_PNG=OFF",
    "-DWITH_TIFF=OFF",
    "-DWITH_WEBP=OFF",
    "-DWITH_OPENEXR=OFF",
    "-DWITH_JASPER=OFF",
    "-DWITH_OPENJPEG=OFF",
    "-DWITH_KLEIDICV=OFF",
    "-DWITH_OPENVX=OFF",
    "-DWITH_ADE=OFF",
    "-DWITH_VTK=OFF",
    "-DWITH_CAROTENE=OFF",
    "-DWITH_CPUFEATURES=OFF",
    "-DCV_ENABLE_INTRINSICS=ON",
    "-DOPENCV_ENABLE_NONFREE=OFF",
    "-DENABLE_PRECOMPILED_HEADERS=OFF",
    "-DCMAKE_BUILD_TYPE=Release",
    "-DCMAKE_INSTALL_PREFIX=" + install,
]

run(
    "cmake -S %s -B %s -G 'Unix Makefiles' "
    "-DCMAKE_TOOLCHAIN_FILE=%s/build/cmake/android.toolchain.cmake "
    "-DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-29 %s"
    % (os.path.abspath("opencv-5.1.0"), build, ndk, " ".join(flags))
)

run(f"cmake --build {build} --target opencv_video -j{max(1, os.cpu_count() or 2)}")
run(f"cmake --install {build}")

libs = os.path.join(install, "sdk/native/staticlibs/arm64-v8a")
includes = os.path.join(install, "sdk/native/jni/include/opencv2")
video_lib = os.path.join(libs, "libopencv_video.a")
video_headers = os.path.join(includes, "video")

if not os.path.isfile(video_lib):
    raise SystemExit("libopencv_video.a manquant")
if not os.path.isfile(os.path.join(video_headers, "tracking.hpp")):
    raise SystemExit("opencv2/video/tracking.hpp manquant")

stage = os.path.abspath("stage")
run(f"rm -rf {stage} && mkdir -p {stage}/opencv2")
run(f"cp {video_lib} {stage}/")
run(f"cp -r {video_headers} {stage}/opencv2/")

os.makedirs(EXPORT, exist_ok=True)
out_path = os.path.join(EXPORT, OUTPUT)
with tarfile.open(out_path, "w:gz") as archive:
    for root, _dirs, files in os.walk(stage):
        for name in files:
            full = os.path.join(root, name)
            archive.add(full, os.path.relpath(full, stage))

print(f"Archive créée avec succès : {out_path} ({os.path.getsize(out_path) // (1024 * 1024)} Mo)", flush=True)
          
