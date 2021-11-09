#! /bin/bash
tarup () {
    local dir archive dt
    dir="$1"
    archive="$dir.tar.bz2"
    rm -f "$archive"
    dt=$(git log --oneline -n 1 --format=%cI -- "$dir")
    # Use "-H ustar" to avoid time stamps in archive
    tar cvvj --owner=0 --group=0 --numeric-owner --exclude="*~" \
        --mtime "$dt" -H ustar \
        -f "$archive" "$dir"
}
trap 'echo error in $BASH_COMMAND >&2; exit 1' ERR
export LC_ALL=C.UTF-8
[[ $1 ]]
[[ -d "$1" ]]
[[ -f "$1"/suse-module-tools.spec ]]
ME=$(basename "$0")
tarup modprobe.conf
tarup kernel-scriptlets
rsync -ric \
      --exclude "$ME" \
      --exclude '*~' \
      --exclude .git \
      --exclude .osc \
      --exclude \*.changes \
      --exclude modprobe.conf \
      --exclude kernel-scriptlets \
      --delete \
      ./ "$1"
