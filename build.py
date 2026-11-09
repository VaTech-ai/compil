#!/usr/bin/env python3
"""CueSub - OpenCV 5.1.0 `video` (arm64-v8a, statique).

Port fidele du notebook Kaggle, pour GitHub Actions (ou n'importe quel Linux x86_64).
Produit un seul fichier : out/video-arm64.tar.gz
  - libopencv_video.a
  - opencv2/video/*.hpp (+ detail/, legacy/)
"""
import hashlib
import os
import subprocess
import sys
import tarfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("WORK_DIR", os.path.join(ROOT, "work"))
EXPORT = os.environ.get("EXPORT_DIR", os.path.join(ROOT, "out"))

SRC_TAR = "opencv-5.1.0.tar.gz"
SRC_MD5 = "0cc6c9bd199223be79acd7a9a66bf896"
SRC_URL = "https://github.com/opencv/opencv/archive/refs/tags/5.1.0.tar.gz"

NDK_ZIP = "android-ndk-r25c-linux.zip"
NDK_SHA1 = "53af80a1cce9144025b81c78c8cd556bff42bd0e"  # valeur publiee par Google pour r25c
NDK_URL = "https://dl.google.com/android/repository/android-ndk-r25c-linux.zip"

OUTPUT = "video-arm64.tar.gz"


def run(command):
    print("+ " + command, flush=True)
    subprocess.run(command, shell=True, check=True)


def digest_of(path, algo):
    digest = hashlib.new(algo)
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url, target, attempts=4):
    if os.path.exists(target) and os.path.getsize(target) > 1024 * 1024:
        print("deja present: " + target, flush=True)
        return
    for attempt in range(1, attempts + 1):
        try:
            print("telechargement %s (essai %d/%d)" % (url, attempt, attempts), flush=True)
            urllib.request.urlretrieve(url, target + ".part")
            os.replace(target + ".part", target)
            print("%s -> %d Mo" % (target, os.path.getsize(target) // (1024 * 1024)), flush=True)
            return
        except Exception as error:  # reseau: on retente
            print("echec: %r" % (error,), flush=True)
            if attempt == attempts:
                raise
            time.sleep(5 * attempt)


def main():
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(EXPORT, exist_ok=True)
    os.chdir(WORK)
    print("cpus: %d" % (os.cpu_count() or 1), flush=True)

    # 1) Telechargements + verifications
    fetch(SRC_URL, SRC_TAR)
    got = digest_of(SRC_TAR, "md5")
    print("sources md5: " + got, flush=True)
    if got != SRC_MD5:
        raise SystemExit("sources inattendues: %s" % got)

    fetch(NDK_URL, NDK_ZIP)
    got = digest_of(NDK_ZIP, "sha1")
    print("ndk sha1: " + got, flush=True)
    if got != NDK_SHA1:
        raise SystemExit("NDK inattendu: %s" % got)

    if not os.path.isdir("opencv-5.1.0"):
        run("tar -xzf " + SRC_TAR)
    if not os.path.isdir("android-ndk-r25c"):
        run("unzip -q " + NDK_ZIP)

    # 2) Configuration CMake (memes options que le notebook)
    ndk = os.path.join(WORK, "android-ndk-r25c")
    build = os.path.join(WORK, "build-arm64")
    install = os.path.join(WORK, "android-out")

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
        % (os.path.join(WORK, "opencv-5.1.0"), build, ndk, " ".join(flags))
    )

    # 3) Compilation
    run("cmake --build %s --target opencv_video -j%d" % (build, max(1, os.cpu_count() or 2)))

    # 4) Installation + verifications
    run("cmake --install %s" % build)

    libs = os.path.join(install, "sdk/native/staticlibs/arm64-v8a")
    includes = os.path.join(install, "sdk/native/jni/include/opencv2")
    video_lib = os.path.join(libs, "libopencv_video.a")
    video_headers = os.path.join(includes, "video")
    if not os.path.isfile(video_lib):
        raise SystemExit("libopencv_video.a manquant")
    if not os.path.isfile(os.path.join(video_headers, "tracking.hpp")):
        raise SystemExit("opencv2/video/tracking.hpp manquant")

    # 5) Archive finale
    stage = os.path.join(WORK, "stage")
    run("rm -rf %s && mkdir -p %s/opencv2" % (stage, stage))
    run("cp %s %s/" % (video_lib, stage))
    run("cp -r %s %s/opencv2/" % (video_headers, stage))

    out_path = os.path.join(EXPORT, OUTPUT)
    with tarfile.open(out_path, "w:gz") as archive:
        for root, _dirs, files in os.walk(stage):
            for name in sorted(files):
                full = os.path.join(root, name)
                archive.add(full, os.path.relpath(full, stage))

    print("archive: %s (%.1f Mo, md5 %s)" % (OUTPUT, os.path.getsize(out_path) / 1048576.0, digest_of(out_path, "md5")), flush=True)
    print("lib: %d o, md5 %s" % (os.path.getsize(video_lib), digest_of(video_lib, "md5")), flush=True)
    with tarfile.open(out_path, "r:gz") as reader:
        for member in reader.getmembers():
            print("%10d o  %s" % (member.size, member.name), flush=True)


if __name__ == "__main__":
    sys.exit(main())
        
