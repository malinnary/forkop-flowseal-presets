#!/bin/sh
# Installs files only; never applies a preset or resets the user's configuration.
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
fail() { echo "ERROR: $*" >&2; exit 1; }
[ "$(id -u)" = 0 ] || fail 'Run as root'
[ -r /etc/openwrt_release ] || fail 'OpenWrt is required'
(cd "$base" && sha256sum -c SHA256SUMS >/dev/null) || fail 'Damaged installation package'
lock=/tmp/flowseal-presets.lock
mkdir "$lock" 2>/dev/null || fail 'Another operation or stale lock exists; inspect before retrying'
echo $$ > "$lock/pid"
backup=''; copying=no
finish() {
 code=$?
 if [ "$code" -ne 0 ] && [ "$copying" = yes ]; then
  while IFS= read -r rel; do
   if [ -f "$backup/root/$rel" ]; then cp -p "$backup/root/$rel" "/$rel"; else rm -f "/$rel"; fi
  done < "$base/install-files.txt"
  echo "Switcher files rolled back. Backup: $backup" >&2
 fi
 rm -f "$lock/pid" "$lock/check.srs"; rmdir "$lock" 2>/dev/null || true
}
trap finish EXIT
trap 'exit 130' HUP INT TERM
[ -z "$(uci changes forkop 2>/dev/null || true)" ] || fail 'Save/discard pending Forkop changes first'
if ! command -v forkop >/dev/null 2>&1; then
 for old in /etc/config/forkop /etc/config/podkop /etc/config/podkop-plus /etc/config/podkop_plus; do
  [ ! -e "$old" ] || fail "Existing configuration without supported Forkop: $old; manual review needed"
 done
fi
sh "$base/dependencies.sh" "$base"
for cmd in forkop sing-box ucode setsid jsonfilter; do command -v "$cmd" >/dev/null || fail "Missing $cmd"; done
[ -r /usr/lib/forkop/providers/zapret/validator.uc ] || fail 'Unsupported Forkop API'
[ -x /opt/zapret/nfq/nfqws ] || fail 'Missing nfqws'
for dir in /www/luci-static/resources/view /usr/share/luci/menu.d /usr/share/rpcd/acl.d; do
 [ -d "$dir" ] || fail "Missing LuCI directory: $dir"
done
if [ -f /etc/forkop-flowseal/active ]; then
 while IFS= read -r rel; do
  case "$rel" in usr/share/forkop-flowseal/presets-v2/*)
   [ -f "/$rel" ] || fail "Missing active asset: $rel"
   # Older Windows-built packages used CRLF; only line endings may change.
   a=$(tr -d '\r' < "$base/root/$rel" | sha256sum)
   b=$(tr -d '\r' < "/$rel" | sha256sum)
   [ "$a" = "$b" ] || fail "Active assets differ: $rel; restore/review before upgrading";;
  usr/share/forkop-flowseal/upstream/bin/*)
   cmp -s "$base/root/$rel" "/$rel" || fail "Active payload differs: $rel";; esac
 done < "$base/install-files.txt"
fi
changed=no
while IFS= read -r rel; do
 cmp -s "$base/root/$rel" "/$rel" || changed=yes
done < "$base/install-files.txt"
if [ "$changed" = no ]; then echo 'Already installed; nothing changed.'; exit 0; fi
available=$(df -Pk /overlay | awk 'END {print $4}')
[ "$available" -ge 4096 ] || fail 'At least 4 MiB free flash is required for switcher + backup'
backup=$(mktemp -d /root/flowseal-install-backup-XXXXXX)
chmod 700 "$backup"
while IFS= read -r rel; do
 [ ! -L "/$rel" ] || fail "Refusing symlink: /$rel"
 if [ -e "/$rel" ]; then
  [ -f "/$rel" ] || fail "Not a regular file: /$rel"
  mkdir -p "$backup/root/$(dirname "$rel")"
  cp -p "/$rel" "$backup/root/$rel"
 fi
done < "$base/install-files.txt"
cp "$base/install-files.txt" "$backup/install-files.txt"
copying=yes
while IFS= read -r rel; do
 mkdir -p "/$(dirname "$rel")"
 cp -p "$base/root/$rel" "/$rel"
done < "$base/install-files.txt"
echo 'Validating all 22 presets against the installed components...'
for opts_file in /usr/share/forkop-flowseal/presets-v2/*/*.opts; do
 opts=$(tr -d '\r' < "$opts_file")
 ucode -L /usr/lib/forkop /usr/lib/forkop/providers/zapret/validator.uc validate-json nfqws "$opts" >/dev/null
 (set -f; /opt/zapret/nfq/nfqws --dry-run --qnum=65534 $opts) >/dev/null 2>&1
 sing-box rule-set compile --output "$lock/check.srs" "${opts_file%.opts}.json" >/dev/null 2>&1
done
/etc/init.d/rpcd restart
copying=no
echo "Switcher installed. Backup: $backup"
echo 'Open Services -> Flowseal Presets. Existing rules and active preset were preserved.'
echo 'New installation: select Check, then Apply. No preset was applied by this installer.'
