#!/bin/sh
# 不依赖系统 Python；先验证固定制品与整个运行目录，再调用管理入口。
set -eu
LC_ALL=C; export LC_ALL
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
fail() { printf '%s\n' "$1" >&2; exit 1; }
hash() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum | awk '{print $1}';
  else shasum -a 256 | awk '{print $1}'; fi
}
os=$(uname -s); arch=$(uname -m)
case "$os:$arch" in
  Darwin:arm64|Darwin:aarch64) key=darwin-arm64;;
  Darwin:x86_64) key=darwin-x86_64;;
  Linux:x86_64) key=linux-x86_64;;
  Linux:aarch64|Linux:arm64) key=linux-aarch64;;
  *) fail "unsupported_python_platform: $os $arch";;
esac
line=$(awk -F '\t' -v key="$key" '$1==key {print}' "$HERE/python-platforms.tsv")
[ -n "$line" ] || fail unsupported_python_platform
tab=$(printf '\t')
IFS="$tab" read -r selected version url archive_sha executable manifest manifest_sha minimum <<EOF
$line
EOF
case "$key" in
  darwin-*) actual_system=$(sw_vers -productVersion);;
  linux-*) actual_system=$(getconf GNU_LIBC_VERSION 2>/dev/null | awk '$1=="glibc" {print $2}');;
esac
[ -n "$actual_system" ] || fail unsupported_system_libc
awk -v actual="$actual_system" -v minimum="$minimum" 'BEGIN { split(actual,a,"."); split(minimum,b,"."); for(i=1;i<=3;i++){if(a[i]+0>b[i]+0)exit 0;if(a[i]+0<b[i]+0)exit 1} }' || fail "minimum_system_required: $minimum"
base=${CRAFT_PYTHON_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/craft-runtimes/python}
case "$base" in /*) ;; *) fail python_home_must_be_absolute;; esac
case "$base/" in "$HERE/"*) fail python_home_inside_skill;; esac
[ ! -L "$base" ] || fail python_home_symlink
read_only=0
for argument in "$@"; do [ "$argument" != doctor ] || read_only=1; done
if [ "$read_only" = 1 ] && [ ! -d "$base/$version-$key" ]; then
  # 不依赖Python转义实际入口路径，避免空格、引号或控制字符破坏JSON。
  entry_json=$(printf '%s\n' "$HERE/launch.sh" | awk '
    BEGIN { printf "\""; for (n=1;n<32;n++) esc[sprintf("%c",n)]=sprintf("\\u%04x",n) }
    { if(NR>1) printf "\\n"; for(i=1;i<=length($0);i++) {
        c=substr($0,i,1); if(c=="\\" || c=="\"") printf "\\%s",c;
        else if(c in esc) printf "%s",esc[c]; else printf "%s",c
    }} END { printf "\"" }')
  printf '{"platform":"%s","python":{"version":"%s","installed":false},"runtimeAcceptance":"NOT_RUN","recovery":"launch run prepares the pinned isolated Python","recoveryActions":[{"id":"prepare_pinned_python","argv":["sh",%s,"--python-version"],"automatic":false}]}\n' "$key" "$version" "$entry_json"
  exit 0
fi
destination="$base/$version-$key"
lock=''
if [ "$read_only" != 1 ]; then
  mkdir -p "$base"
  lock="$destination.lock"
  waited=0
  until mkdir "$lock" 2>/dev/null; do
    waited=$((waited+1)); [ "$waited" -lt 120 ] || fail python_install_busy
    sleep 1
  done
fi
stage=''
cleanup() { [ -z "$stage" ] || rm -rf -- "$stage"; [ -z "$lock" ] || rmdir "$lock"; }
trap cleanup EXIT
trap 'exit 130' INT TERM
[ "$(hash < "$HERE/$manifest")" = "$manifest_sha" ] || fail python_manifest_checksum_mismatch
verify() {
  root=$1
  [ ! -L "$root" ] || fail python_runtime_symlink
  expected_count=$(wc -l < "$HERE/$manifest" | tr -d ' ')
  actual_count=$(find "$root" \( -type f -o -type l \) ! -path "$root/installation.json" -print | wc -l | tr -d ' ')
  [ "$actual_count" = "$expected_count" ] || fail python_runtime_inventory_changed
  while IFS="$tab" read -r kind expected relative; do
    case "$relative" in /*|../*|*/../*) fail unsafe_python_manifest;; esac
    file="$root/$relative"
    if [ "$kind" = l ]; then
      [ -L "$file" ] || fail python_link_missing
      target=$(readlink "$file")
      actual=$(printf '%s' "$target" | hash)
    else
      [ -f "$file" ] && [ ! -L "$file" ] || fail python_file_missing
      actual=$(hash < "$file")
    fi
    [ "$actual" = "$expected" ] || fail "python_installed_checksum_mismatch: $relative"
  done < "$HERE/$manifest"
}
if [ ! -e "$destination" ] && [ ! -L "$destination" ]; then
  stage=$(mktemp -d "$base/.python-XXXXXXXX")
  archive=${CRAFT_PYTHON_ARCHIVE:-$stage/python.tar.gz}
  if [ -z "${CRAFT_PYTHON_ARCHIVE:-}" ]; then
    curl --fail --location --proto '=https' --proto-redir '=https' --retry 2 --connect-timeout 15 --max-time 240 --max-filesize 268435456 "$url" -o "$archive"
  fi
  [ "$(hash < "$archive")" = "$archive_sha" ] || fail python_archive_checksum_mismatch
  mkdir "$stage/payload"
  # 仅解包已匹配内置固定摘要的发行包，不接受调用方指定的新锁。
  tar -xzf "$archive" -C "$stage/payload"
  verify "$stage/payload"
  printf '{"version":"%s","platform":"%s","archiveSha256":"%s"}\n' "$version" "$key" "$archive_sha" > "$stage/payload/installation.json"
  mv "$stage/payload" "$destination"
else
  verify "$destination"
fi
cleanup; stage=''; trap - EXIT INT TERM
if [ "${1:-}" = --python-version ]; then
  exec "$destination/$executable" -I -B --version
fi
exec "$destination/$executable" -I -B "$HERE/managed.py" "$@"
