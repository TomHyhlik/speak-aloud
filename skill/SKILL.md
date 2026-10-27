---
name: speak-aloud
description: Say the response out loud through the machine's speakers. Use whenever the user asks to hear the answer — a bare "aloud" (speak the previous response), "tell me aloud", "say it aloud", "read it out loud", "speak to me", "say that", "read this to me", "voice mode on" — or asks to stop talking ("stop speaking", "shut up", "be quiet", "voice mode off").
---

# Speak the response aloud

Speech goes through the user's own tool:

```
/home/tomas/Repos/speak-aloud/speak.sh
```

It speaks with Piper (a natural local voice), falling back to `spd-say`,
strips Markdown, and by default interrupts anything already being spoken.

## "Aloud" on its own means the last response

When the message is just "aloud", "tell me aloud", "say it aloud", "read it
aloud" or similar, with no new question, speak a spoken version of your
**previous** response. Don't re-answer anything or add new content; reply
on screen with one short line such as "Reading that aloud."

When "aloud" comes with a new question ("tell me aloud what changed"),
answer that question and speak the answer, as below.

## How to answer

1. Work out the answer as usual.
2. Write a **spoken version**: plain conversational sentences, no code,
   tables, file paths or URLs read out character by character. Keep it short —
   roughly what a person would say out loud, a few sentences. Summarise long
   or technical answers and mention that the details are on screen.
3. Speak it, passing the text on stdin through a quoted heredoc so quotes and
   `$` signs survive:

   ```bash
   /home/tomas/Repos/speak-aloud/speak.sh <<'SPEECH'
   The build passed. Two tests were flaky, and the details are on screen.
   SPEECH
   ```

   Don't add `--wait`: the script returns straight away while speech plays,
   so the turn isn't blocked.
4. Still show the full answer as text in the reply.

Match the user's language with `--lang` (an ISO code such as `cs`, `de`,
`en`) when they speak to you in something other than English. Only English
has a Piper voice installed; other languages fall back to the robotic
espeak voice unless a Piper voice for them is added (see the tool's README).

## Voice mode on / off

"Voice mode on" (or similar) means speak every response for the rest of the
conversation until they say it's off. Otherwise speak only the answers the
user asked to hear.

## Stopping

When the user asks to stop or be quiet, run:

```bash
/home/tomas/Repos/speak-aloud/speak.sh --stop
```

## Options

`--rate N` (-100..100) changes the speed and `--voice NAME` picks a Piper
voice from `~/.local/share/speak-aloud/voices`; `--help` lists everything.
