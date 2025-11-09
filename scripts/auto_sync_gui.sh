#!/bin/bash
# Auto-click "Yes/Download" button in Anki's initial sync dialog
# Language-agnostic: just presses Enter on the default button

TIMEOUT=30
echo "[*] Waiting for Anki sync dialog..."

# Wait for Anki dialog window (not main window)
elapsed=0
while [ $elapsed -lt $TIMEOUT ]; do
    # Look for all Anki windows
    ALL_WINDOWS=$(xdotool search --name "Anki" 2>/dev/null || echo "")

    if [ -n "$ALL_WINDOWS" ]; then
        for WINDOW in $ALL_WINDOWS; do
            # Get window info
            GEOMETRY=$(xdotool getwindowgeometry "$WINDOW" 2>/dev/null || echo "")
            TITLE=$(xdotool getwindowname "$WINDOW" 2>/dev/null || echo "")

            # Skip Qt internal windows
            if echo "$TITLE" | grep -qi "Qt Selection Owner"; then
                continue
            fi

            # Extract width and height
            if echo "$GEOMETRY" | grep -q "Geometry:"; then
                WIDTH=$(echo "$GEOMETRY" | grep "Geometry:" | awk '{print $2}' | cut -d'x' -f1)
                HEIGHT=$(echo "$GEOMETRY" | grep "Geometry:" | awk '{print $2}' | cut -d'x' -f2)

                # Dialog windows: between 200-600px wide, 80-400px tall
                # This filters out tiny windows (1x1) and the main app window (1024x745)
                if [ "$WIDTH" -gt 200 ] && [ "$WIDTH" -lt 600 ] && [ "$HEIGHT" -gt 80 ] && [ "$HEIGHT" -lt 400 ]; then
                    echo "[*] Sync dialog detected, clicking 'Download' button..."
                    xdotool windowactivate "$WINDOW" 2>/dev/null
                    sleep 0.5
                    xdotool key Return
                    echo "[OK] Automatic sync initiated"
                    exit 0
                fi
            fi
        done
    fi

    sleep 1
    elapsed=$((elapsed + 1))
done

echo "[INFO] No dialog detected - sync may not be needed"
exit 0
