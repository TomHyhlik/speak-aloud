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
./speak.sh --dry-run "..."   # show what would be spoken
```

New speech interrupts whatever is playing; pass `--queue` to wait in line
instead, or `--wait` to block until it finishes. Defaults can be set with
`SPEAK_LANG`, `SPEAK_RATE`, `SPEAK_VOICE` and `SPEAK_ENGINE`.

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
