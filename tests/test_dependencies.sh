#!/bin/sh
# Hermetic control-flow tests. Package manager, downloads and components are MOCKS.
# Run with: sh tests/test_dependencies.sh files/dependencies.sh
set -eu
source_file=$1
suite=$(mktemp -d /tmp/flowseal-mocks-XXXXXX)
trap 'rm -rf "$suite"' EXIT
for scenario in existing missing-apk missing-opkg unsupported bad-checksum; do
 sandbox="$suite/$scenario"; mkdir -p "$sandbox/luci-view"
 sed -e "s@/opt/zapret/nfq/nfqws@$sandbox/nfqws@g" \
     -e "s@/www/luci-static/resources/view@$sandbox/luci-view@g" \
     "$source_file" > "$sandbox/dependencies.sh"
 printf 'expected  forkop_1.0.5.apk\nexpected  forkop_1.0.5.ipk\nexpected  luci-app-forkop_1.0.5.apk\nexpected  luci-app-forkop_1.0.5.ipk\nexpected  luci-i18n-forkop-ru_1.0.5.apk\nexpected  luci-i18n-forkop-ru_1.0.5.ipk\n' > "$sandbox/forkop-packages.sha256"
 case "$scenario" in existing|unsupported) touch "$sandbox/installed" "$sandbox/nfqws"; chmod +x "$sandbox/nfqws";; esac
 # Separate shell keeps set -e effective, unlike a function called in `if`.
 export scenario sandbox
 cat > "$sandbox/harness.sh" <<'MOCK'
set -eu
command() {
 case "$2" in
 apk) [ "$scenario" != missing-opkg ]; return;;
 opkg) [ "$scenario" = missing-opkg ]; return;;
 forkop) [ -f "$sandbox/installed" ]; return;;
 sing-box) [ "$scenario" = existing ] || [ "$scenario" = unsupported ]; return;;
 *) return 0;; esac
}
df() { printf 'Filesystem 1024-blocks Used Available Capacity Mounted\nfake 200000 1000 199000 1%% /overlay\n'; }
apk() { printf 'apk %s\n' "$*" >> "$sandbox/actions"; [ "$1" != add ] || touch "$sandbox/installed"; return 0; }
opkg() { printf 'opkg %s\n' "$*" >> "$sandbox/actions"; [ "$1" != install ] || touch "$sandbox/installed"; return 0; }
curl() { while [ "$#" -gt 0 ]; do if [ "$1" = -o ]; then shift; touch "$1"; break; fi; shift; done; }
sha256sum() { cat >/dev/null; [ "$scenario" != bad-checksum ]; }
forkop() {
 if [ "$1" = show_version ]; then
  if [ "$scenario" = unsupported ]; then echo 2.0.0; else echo 1.0.5; fi
 else
  echo "component $*" >> "$sandbox/actions"
  if [ "$2" = zapret ]; then touch "$sandbox/nfqws"; chmod +x "$sandbox/nfqws"; fi
 fi
}
. "$sandbox/dependencies.sh" "$sandbox"
MOCK
 result=0; sh "$sandbox/harness.sh" "$sandbox" > "$sandbox/output" 2>&1 || result=$?
 cat "$sandbox/output"
 case "$scenario" in
 existing) [ "$result" = 0 ]; [ ! -e "$sandbox/actions" ];;
 missing-apk|missing-opkg) [ "$result" = 0 ]; grep -q '1.0.5' "$sandbox/actions"; grep -q 'component component_action sing_box install_stable' "$sandbox/actions"; grep -q 'component component_action zapret install' "$sandbox/actions";;
 unsupported|bad-checksum) [ "$result" != 0 ]; [ ! -e "$sandbox/actions" ];;
 esac
 echo "PASS mock: $scenario"
done
