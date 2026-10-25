#!/bin/sh
# viewport's UI tests: drives the example app (examples/main.tsl) without a
# window, with the mouse, keys and buttons, and checks where the view is
# afterwards from the status line ("center x, y · scale pt/m · angle°").
# Run from anywhere: sh tests/ui.sh
#
# Author: Alexius Academia
# Date: 2026-10-25

cd "$(dirname "$0")/.." || exit 1
TESSEL="${TESSEL:-tessel}"
failed=0
passed=0

# check NAME SCRIPT EXPECTED... : every EXPECTED text must be in the output.
check() {
    name="$1"
    script="$2"
    shift 2
    out=$(TESSEL_SCRIPT="$script" "$TESSEL" run examples 2>&1)
    for want in "$@"; do
        if printf '%s\n' "$out" | grep -qF -- "$want"; then
            :
        else
            echo "FAIL  $name: no \"$want\""
            printf '%s\n' "$out" | grep -E 'Text "mouse|^script|error' | sed 's/^/        /'
            failed=$((failed + 1))
            return
        fi
    done
    echo "ok    $name"
    passed=$((passed + 1))
}

nl='
'
start='center 32.00, 15.00 · 6.506 pt/m · 0.0°'

check "starts with the whole plan" "tree" "$start" 'Canvas (18 fills, 82 strokes, 15 texts)'
check "the wheel zooms about the mouse" "wheel 300 300 0 -100${nl}tree" \
    'center 27.16, 13.02 · 10.727 pt/m'
check "a pinch zooms" "pinch 300 300 1${nl}tree" 'center 25.85, 12.48 · 13.012 pt/m'
check "a drag pans" "press 300 300${nl}move 350 280${nl}release${nl}tree" \
    'center 24.31, 11.93 · 6.506 pt/m'
check "a right drag turns" "press 600 250 right${nl}move 380 60${nl}release${nl}tree" \
    'center 32.00, 15.00 · 6.506 pt/m · 85.5°'
check "rulers hide while turned" "press 600 250 right${nl}move 380 60${nl}release${nl}tree" \
    'Canvas (15 fills, 48 strokes, 6 texts)'
check "a zoom box starts smoothly" "mods shift${nl}press 200 200${nl}move 400 330${nl}release${nl}mods none${nl}wait 0.1${nl}tree" \
    'center 21.25, 15.29 · 17.024 pt/m'
check "and ends where the box was" "mods shift${nl}press 200 200${nl}move 400 330${nl}release${nl}mods none${nl}wait 0.4${nl}tree" \
    'center 19.70, 15.33 · 22.190 pt/m'
check "a double click fits" "mods shift${nl}press 200 200${nl}move 400 330${nl}release${nl}mods none${nl}wait 0.4${nl}doubleclick 300 300${nl}wait 0.5${nl}tree" \
    "$start"
check "Fit" "press 300 300${nl}move 350 280${nl}release${nl}click \"Fit\"${nl}wait 0.5${nl}tree" "$start"
check "+ zooms in" "key +${nl}wait 0.5${nl}tree" 'center 32.00, 15.00 · 9.759 pt/m'
check "the − button zooms out" "click \"−\"${nl}wait 0.5${nl}tree" 'center 32.00, 15.00 · 4.337 pt/m'
check "0 fits" "key +${nl}wait 0.5${nl}key 0${nl}wait 0.5${nl}tree" "$start"
check "the arrows pan" "key left${nl}key up${nl}tree" 'center 17.40, 23.52 · 6.506 pt/m'
check "[ turns" "key [${nl}wait 0.5${nl}tree" '6.506 pt/m · 15.0°'
check "North up" "key [${nl}wait 0.5${nl}click \"North up\"${nl}wait 0.5${nl}tree" "$start"
check "without Smooth, at once" "click \"Smooth\"${nl}key +${nl}tree" 'center 32.00, 15.00 · 9.759 pt/m'
check "Keep in sight stops a long drag" "click \"Keep in sight\"${nl}press 300 300${nl}move 2000 300${nl}release${nl}tree" \
    'center -58.26, 15.00'
check "without it, the plan goes" "press 300 300${nl}move 2000 300${nl}release${nl}tree" 'center -229.29, 15.00'
check "Grid off" "click \"Grid\"${nl}tree" 'Canvas (18 fills, 43 strokes, 15 texts)'
check "Rulers off" "click \"Rulers\"${nl}tree" 'Canvas (15 fills, 44 strokes, 6 texts)'
check "a resize keeps the middle" "size 1000 600${nl}tree" "$start"

echo "$passed passed, $failed failed"
[ "$failed" -eq 0 ]
