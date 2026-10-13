#!/usr/bin/env bash
set -euo pipefail

root=$(dirname -- "$(dirname -- "$(readlink -f -- "$0")")")
output="$root/build"
mkdir -p -- "$output"

if command -v x86_64-w64-mingw32-gcc >/dev/null 2>&1; then
    x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror \
        -ffreestanding -fno-stack-protector -nostdlib \
        -Wl,--entry,mainCRTStartup -Wl,--subsystem,windows \
        "$root/src/notification-clickthrough.c" -o "$output/ctrader-overlay-fix.exe" \
        -luser32 -lkernel32
else
    wine_include=${WINE_INCLUDE_DIR:-/usr/include/wine/windows}
    wine_crt=${WINE_CRT_INCLUDE_DIR:-/usr/include/wine/msvcrt}
    wine_lib=${WINE_LIB_DIR:-/usr/lib/wine/x86_64-windows}
    clang --target=x86_64-w64-windows-gnu -std=c11 -O2 -Wall -Wextra -Werror \
        -ffreestanding -fno-stack-protector -D__WINE_PE_BUILD \
        -I "$wine_include" -I "$wine_crt" -c "$root/src/notification-clickthrough.c" \
        -o "$output/notification-clickthrough.obj"
    lld-link /entry:mainCRTStartup /subsystem:windows /nodefaultlib \
        "/out:$output/ctrader-overlay-fix.exe" "$output/notification-clickthrough.obj" \
        "$wine_lib/libuser32.a" "$wine_lib/libkernel32.a"
fi

printf 'Helper built: %s\n' "$output/ctrader-overlay-fix.exe"
