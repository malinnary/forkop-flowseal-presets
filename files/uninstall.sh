#!/bin/sh
set -eu
[ "$(id -u)" = 0 ] || exit 1
if [ -f /etc/forkop-flowseal/active ]; then
 /usr/sbin/flowseal-presets restore
fi
if uci show forkop | grep -q '^forkop\.fs_block_'; then
 echo 'Managed rules remain: refusing removal' >&2; exit 1
fi
backup=$(mktemp -d /root/flowseal-uninstalled-XXXXXX)
chmod 700 "$backup"
index=0
for path in /usr/share/forkop-flowseal /usr/sbin/flowseal-presets /www/luci-static/resources/view/flowseal-presets.js /usr/share/luci/menu.d/flowseal-presets.json /usr/share/rpcd/acl.d/flowseal-presets.json /etc/forkop-flowseal; do
 if [ -e "$path" ]; then
  mv "$path" "$backup/item-$index"
  printf '%s %s\n' "item-$index" "$path" >> "$backup/paths.txt"
 fi
 index=$((index+1))
done
/etc/init.d/rpcd restart
echo "Removed from active paths; recoverable files saved in $backup"
