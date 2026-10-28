#!/bin/sh
set -eu
base=$1
fail() { echo "ERROR: $*" >&2; exit 1; }
if command -v apk >/dev/null 2>&1; then pm=apk; ext=apk
elif command -v opkg >/dev/null 2>&1; then pm=opkg; ext=ipk
else fail 'Neither apk nor opkg is available'; fi
updated=no
packages() {
 if [ "$updated" = no ]; then "$pm" update; updated=yes; fi
 if [ "$pm" = apk ]; then apk add "$@"; else opkg install "$@"; fi
}
if command -v forkop >/dev/null 2>&1; then
 version=$(forkop show_version)
 case "$version" in 1.0.5) ;; *) fail "Forkop $version is not validated (expected 1.0.5); not upgrading or downgrading";; esac
 echo "Forkop $version found; keeping installed version."
else
 available=$(df -Pk /overlay | awk 'END {print $4}')
 [ "$available" -ge 40960 ] || fail 'New Forkop installation requires at least 40 MiB free flash'
 command -v curl >/dev/null 2>&1 || packages curl ca-bundle
 for name in forkop luci-app-forkop luci-i18n-forkop-ru; do
  file="${name}_1.0.5.$ext"
  curl --proto '=https' --proto-redir '=https' --connect-timeout 20 --max-time 300 --retry 2 -fL \
   "https://github.com/ushan0v/forkop/releases/download/1.0.5/$file" -o "$base/$file"
  expected=$(awk -v name="$file" '$2==name {print $1}' "$base/forkop-packages.sha256")
  [ -n "$expected" ] || fail "No pinned checksum for $file"
  printf '%s  %s\n' "$expected" "$base/$file" | sha256sum -c - || fail 'Forkop checksum mismatch'
 done
 [ "$updated" = yes ] || { "$pm" update; updated=yes; }
 if [ "$pm" = apk ]; then
  apk add --allow-untrusted "$base/forkop_1.0.5.apk" "$base/luci-app-forkop_1.0.5.apk" "$base/luci-i18n-forkop-ru_1.0.5.apk"
 else
  opkg install "$base/forkop_1.0.5.ipk" "$base/luci-app-forkop_1.0.5.ipk" "$base/luci-i18n-forkop-ru_1.0.5.ipk"
 fi
fi
command -v setsid >/dev/null 2>&1 || packages setsid
[ -d /www/luci-static/resources/view ] || packages luci
# Architecture-specific components are resolved by Forkop, not pinned by this package.
command -v sing-box >/dev/null 2>&1 || forkop component_action sing_box install_stable
[ -x /opt/zapret/nfq/nfqws ] || forkop component_action zapret install
