#! /bin/bash
trap 'echo error in $BASH_COMMAND >&2; exit 1' ERR
export LC_ALL=C.UTF-8
[[ $1 ]]
[[ -d "$1" ]]
[[ -f "$1"/suse-module-tools.spec ]]
ME=$(basename "$0")
rm -f modprobe.conf.tar.bz2
dt=$(git log --oneline -n 1 --format=%cI -- modprobe.conf)
# Use "-H ustar" to avoid time stamps in archive
tar cj --owner=0 --group=0 --numeric-owner \
    --mtime "$dt" -H ustar \
    -f modprobe.conf.tar.bz2 modprobe.conf
rsync -ric \
      --exclude "$ME" \
      --exclude '*~' \
      --exclude .git \
      --exclude modprobe.conf \
      ./ "$1"
