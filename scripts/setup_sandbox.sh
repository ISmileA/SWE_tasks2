#!/usr/bin/env bash
set -euo pipefail
cd /mnt/c/KFU/DM/Task2
mkdir -p vendor/debs
cd vendor/debs
apt download bubblewrap
for package in bubblewrap*.deb; do dpkg-deb -x "$package" ../bubblewrap; done
../bubblewrap/usr/bin/bwrap --version
../bubblewrap/usr/bin/bwrap --ro-bind /usr /usr --symlink usr/lib /lib --symlink usr/lib64 /lib64 --proc /proc --dev /dev --unshare-all --die-with-parent --new-session /usr/bin/true
