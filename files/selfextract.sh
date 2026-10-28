#!/bin/sh
set -eu
[ "$(id -u)" = 0 ] || { echo 'Run as root' >&2; exit 1; }
[ -r /etc/openwrt_release ] || { echo 'OpenWrt required' >&2; exit 1; }
task_dir=$(mktemp -d /tmp/flowseal-setup-XXXXXX)
trap 'rm -rf "$task_dir"' EXIT
trap 'exit 130' HUP INT TERM
line=$(awk '/^__FLOWSEAL_PAYLOAD__$/ {print NR+1; exit}' "$0")
[ -n "$line" ]
tail -n +"$line" "$0" | base64 -d > "$task_dir/package.tar.gz"
printf '%s  %s\n' '@SHA256@' "$task_dir/package.tar.gz" | sha256sum -c - >/dev/null
tar -xzf "$task_dir/package.tar.gz" -C "$task_dir"
sh "$task_dir/install.sh"
exit 0
__FLOWSEAL_PAYLOAD__
