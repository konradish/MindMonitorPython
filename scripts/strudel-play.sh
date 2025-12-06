#!/bin/bash
# Play a Strudel pattern via Windows Chrome
# Usage: ./strudel-play.sh "pattern code" 
#    or: ./strudel-play.sh /path/to/pattern.txt

CHROME_AUTO="C:\\projects\\prompt-kit\\chrome-automation"
PATTERN="$1"

# If it's a file path, copy it; otherwise write the pattern to a temp file
if [[ -f "$PATTERN" ]]; then
    cp "$PATTERN" /mnt/c/projects/prompt-kit/chrome-automation/pattern.txt
else
    echo "$PATTERN" > /mnt/c/projects/prompt-kit/chrome-automation/pattern.txt
fi

powershell.exe -Command "cd $CHROME_AUTO; \$env:CDP_PORT='9223'; node scripts/run-automation.mjs strudel-play-file.mjs pattern.txt" 2>&1
