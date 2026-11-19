#!/usr/bin/env bash
# Speak text aloud. Uses Piper (natural neural voice) when installed,
# otherwise speech-dispatcher's spd-say. Markdown is cleaned up first.
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: speak.sh [options] [TEXT...]

Speaks TEXT, or stdin when no TEXT is given.

Options:
  -f, --file PATH    Read the text from PATH
  -l, --lang CODE    Language ISO code (default: en, or $SPEAK_LANG)
  -r, --rate N       Speech rate -100..100 (default: 0, or $SPEAK_RATE)
  -v, --voice NAME   Piper voice name, e.g. en_US-lessac-medium; with spd-say a
                     voice type such as female1 (default: $SPEAK_VOICE)
  -e, --engine NAME  piper or spd-say (default: piper if installed)
  -w, --wait         Block until speaking has finished
  -q, --queue        Queue after current speech instead of interrupting it
      --raw          Don't strip Markdown
  -L, --last         Open the player window on the newest saved recording and exit
  -s, --stop         Stop all speech and exit
  -n, --dry-run      Print the cleaned text instead of speaking it
  -h, --help         Show this help

Piper lives in $SPEAK_HOME (default ~/.local/share/speak-aloud): a venv in
venv/ and voice models in voices/. See README.md for installing it.
USAGE
}

home="${SPEAK_HOME:-$HOME/.local/share/speak-aloud}"
piper="$home/venv/bin/piper"
pidfile="${XDG_RUNTIME_DIR:-/tmp}/speak-aloud.pid"
lockfile="${XDG_RUNTIME_DIR:-/tmp}/speak-aloud.lock"

lang="${SPEAK_LANG:-en}"
rate="${SPEAK_RATE:-0}"
voice="${SPEAK_VOICE:-}"
engine="${SPEAK_ENGINE:-}"
wait=0 queue=0 raw=0 dry=0 last=0 file=""
args=()

stop_speech() {
  if [[ -f "$pidfile" ]]; then
    while read -r pid; do kill -- -"$pid" 2>/dev/null || true; done < "$pidfile"
    rm -f "$pidfile"
  fi
  command -v spd-say >/dev/null && spd-say -C || true
}

while (($#)); do
  case "$1" in
    -f|--file)   file="$2"; shift 2 ;;
    -l|--lang)   lang="$2"; shift 2 ;;
    -r|--rate)   rate="$2"; shift 2 ;;
    -v|--voice|-t) voice="$2"; shift 2 ;;
    -e|--engine) engine="$2"; shift 2 ;;
    -w|--wait)   wait=1; shift ;;
    -q|--queue)  queue=1; shift ;;
    --raw)       raw=1; shift ;;
    -L|--last)   last=1; shift ;;
    -s|--stop)   stop_speech; rm -f "${XDG_RUNTIME_DIR:-/tmp}/speak-aloud.pos"; exit 0 ;;
    -n|--dry-run) dry=1; shift ;;
    -h|--help)   usage; exit 0 ;;
    --)          shift; args+=("$@"); break ;;
    -*)          echo "speak.sh: unknown option $1" >&2; usage >&2; exit 2 ;;
    *)           args+=("$1"); shift ;;
  esac
done

if ((last)); then
  newest="$(ls -1 "$home/records"/*.mp3 2>/dev/null | tail -n1 || true)"
  [[ -n "$newest" ]] || { echo "speak.sh: no saved recordings yet" >&2; exit 1; }
  stop_speech
  setsid python3 "$(dirname "$(readlink -f "$0")")/player.py" "$newest" </dev/null >/dev/null 2>&1 &
  echo $! >> "$pidfile"
  exit 0
fi

if [[ -n "$file" ]]; then
  text="$(cat -- "$file")"
elif ((${#args[@]})); then
  text="${args[*]}"
else
  text="$(cat)"
fi

clean_markdown() {
  perl -0777 -pe '
    s/```.*?```/ (code omitted) /gs;          # fenced code blocks
    s/!\[([^\]]*)\]\([^)]*\)/$1/g;             # images -> alt text
    s/\[([^\]]+)\]\([^)]*\)/$1/g;              # links -> link text
    s{https?://\S+}{a link}g;                  # bare URLs
    s/`([^`]*)`/$1/g;                          # inline code
    s/^\s{0,3}#{1,6}\s*//mg;                   # headings
    s/^\s*>\s?//mg;                            # blockquotes
    s/^\s*[-*+]\s+//mg;                        # bullets
    s/^\s*\|?\s*:?-{3,}.*$//mg;                # table separator rows
    s/[ \t]*\|[ \t]*/, /g;                     # table cells
    s/(\*\*|__|~~)(.+?)\1/$2/g;                # bold, strikethrough
    s/(?<![\w*])[*_](\S.*?)[*_](?![\w*])/$1/g;  # italics
    s/^[ \t,]+|[ \t,]+$//mg;                   # stray edges
    s/\n{3,}/\n\n/g;
  '
}

((raw)) || text="$(printf '%s' "$text" | clean_markdown)"
[[ -n "${text//[[:space:]]/}" ]] || { echo "speak.sh: nothing to say" >&2; exit 1; }

if ((dry)); then printf '%s\n' "$text"; exit 0; fi

# Pick a Piper model: the named voice, else the first installed one for $lang.
model=""
if [[ -x "$piper" && "$engine" != "spd-say" ]]; then
  if [[ "$voice" == *_* && -f "$home/voices/$voice.onnx" ]]; then
    model="$home/voices/$voice.onnx"
  else
    model="$(ls "$home/voices/${lang}"_*.onnx 2>/dev/null | head -n1 || true)"
  fi
fi
[[ "$engine" == "piper" && -z "$model" ]] && { echo "speak.sh: no Piper voice for '$lang' in $home/voices" >&2; exit 1; }

if [[ -z "$model" ]]; then
  command -v spd-say >/dev/null || { echo "speak.sh: neither Piper nor spd-say is available" >&2; exit 1; }
  ((queue)) || spd-say -C
  cmd=(spd-say -l "$lang" -r "$rate")
  [[ -n "$voice" && "$voice" != *_* ]] && cmd+=(-t "$voice")
  ((wait)) && cmd+=(-w)
  printf '%s\n' "$text" | "${cmd[@]}" -e >/dev/null
  exit 0
fi

# Piper: rate 100 halves phoneme length (faster), -100 makes it 1.5x (slower).
length_scale="$(awk -v r="$rate" 'BEGIN { printf "%.2f", 1 - r / 200 }')"
sample_rate="$(perl -ne 'print $1 if /"sample_rate"\s*:\s*(\d+)/' "$model.json")"

((queue)) || stop_speech
mkdir -p "$home"

# The speech is rendered to a new MP3 in $SPEAK_DIR (the 10 newest are kept,
# older ones deleted), then a small window with playback controls plays it. The window stays open after
# the speech ends; the queue lock is released when playback finishes.
export SPEAK_TEXT="$text" SPEAK_MODEL="$model" SPEAK_PIPER="$piper" \
       SPEAK_LS="$length_scale" SPEAK_SR="${sample_rate:-22050}" \
       SPEAK_LOCK="$lockfile" SPEAK_DIR="$home/records" SPEAK_KEEP="${SPEAK_KEEP:-10}" \
       SPEAK_PLAYER="$(dirname "$(readlink -f "$0")")/player.py" \
       SPEAK_DONE="${XDG_RUNTIME_DIR:-/tmp}/speak-aloud.done.$$"
rm -f "$SPEAK_DONE"
player='
  exec 9>"$SPEAK_LOCK"; flock 9
  mkdir -p "$SPEAK_DIR"
  mp3="$SPEAK_DIR/$(date +%Y%m%d-%H%M%S-%N).mp3"
  tmp="$mp3.part"
  printf "%s\n" "$SPEAK_TEXT" \
    | "$SPEAK_PIPER" -m "$SPEAK_MODEL" --length-scale "$SPEAK_LS" --output-raw 2>/dev/null \
    | gst-launch-1.0 -q fdsrc fd=0 ! \
        rawaudioparse format=pcm pcm-format=s16le sample-rate="$SPEAK_SR" num-channels=1 ! \
        audioconvert ! lamemp3enc target=bitrate cbr=true bitrate=64 ! filesink location="$tmp" \
        >/dev/null 2>&1
  [ -s "$tmp" ] || { rm -f "$tmp"; exit 1; }
  mv -f "$tmp" "$mp3"
  printf "%s\n" "$SPEAK_TEXT" | tr "\n" " " | cut -c1-120 > "${mp3%.mp3}.txt"
  # Keep only the newest $SPEAK_KEEP recordings.
  ls -1 "$SPEAK_DIR"/*.mp3 | head -n -"$SPEAK_KEEP" | while read -r old; do
    rm -f "$old" "${old%.mp3}.txt"
  done
  exec python3 "$SPEAK_PLAYER" "$mp3" >/dev/null 2>&1
'
# Each player runs in its own process group, recorded so --stop can kill it.
setsid bash -c "$player" </dev/null >/dev/null 2>&1 &
echo $! >> "$pidfile"
if ((wait)); then
  # Return when playback has ended (the window stays open for replay).
  while [[ ! -e "$SPEAK_DONE" ]] && kill -0 $! 2>/dev/null; do sleep 0.2; done
  rm -f "$SPEAK_DONE"
fi
