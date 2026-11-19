# speak-aloud

Speaks text aloud on this machine. It uses [Piper](https://github.com/OHF-Voice/piper1-gpl),
a local neural voice, when installed, and falls back to speech-dispatcher's
`spd-say` (espeak-ng, robotic) otherwise or for languages without a Piper voice.

Markdown is stripped first: code blocks become "(code omitted)", links read as
their text, bare URLs as "a link", and table cells are separated by commas.

```bash
./speak.sh "Hello there"
echo "Some **markdown** text" | ./speak.sh
./speak.sh --file notes.md --rate 20
./speak.sh --stop            # silence everything
./speak.sh --last            # reopen the player on the newest recording
./speak.sh --dry-run "..."   # show what would be spoken
```

New speech interrupts whatever is playing; pass `--queue` to wait in line
instead, or `--wait` to block until it finishes. Defaults can be set with
`SPEAK_LANG`, `SPEAK_RATE`, `SPEAK_VOICE` and `SPEAK_ENGINE`.

## The `aloud` command

`aloud` on its own reopens the player on the newest recording; `aloud TEXT`
or `aloud --stop` behave like `speak.sh`. Install it on your PATH with:

```bash
ln -s /home/tomas/Repos/speak-aloud/aloud ~/.local/bin/aloud
```

## Playback window and saved recordings

With Piper, each speech is rendered to an MP3 in
`~/.local/share/speak-aloud/records/`. The 10 newest are kept (change with
`SPEAK_KEEP`); older ones are deleted. A small window (`player.py`, GTK3 +
GStreamer) opens and plays it, with play/pause (space), replay and a seek
slider; **Ctrl+W** closes the window. **Left/Right arrows** skip 5 seconds back/forward, **Up/Down arrows** switch to the older/newer recording, like shell
history; the title line shows `3/10` and the start of the text. The window
stays open after the speech ends so you can replay it, and is replaced by the
next speech or closed by `--stop` (`--wait` and `--queue` still wait for
playback to end, not for the window to close). A new window opens in the
bottom-right corner of the screen; if one is already open, its replacement
appears where you left it. The `spd-say` fallback has no recordings and no
window.

## Installing Piper

```bash
P=~/.local/share/speak-aloud
python3 -m venv $P/venv && $P/venv/bin/pip install piper-tts
mkdir -p $P/voices && cd $P/voices
base=https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium
curl -LO $base/en_US-lessac-medium.onnx -LO $base/en_US-lessac-medium.onnx.json
```

More voices and languages: <https://huggingface.co/rhasspy/piper-voices>. Drop
the `.onnx` and `.onnx.json` pair into `voices/`; the first voice whose name
starts with the `--lang` code is used, or pick one with `--voice NAME`.

## Claude Code skill

`skill/SKILL.md` is the skill that makes Claude read responses aloud on
request ("aloud", "tell me aloud", "voice mode on", "stop speaking"). Install
it globally by linking it into the skills folder:

```bash
ln -s /home/tomas/Repos/speak-aloud/skill ~/.claude/skills/speak-aloud
```
