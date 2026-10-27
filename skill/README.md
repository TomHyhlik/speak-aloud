# speak-aloud skill

An agent skill (`SKILL.md` format) for AI coding agents such as Claude Code.
It makes the agent read its responses aloud through `../speak.sh`. It is
instructions for the agent, not a script to run yourself.

- "aloud" — read the previous response
- "tell me aloud …" — answer the question and speak the answer
- "voice mode on" / "off" — speak every response, or stop doing so
- "stop speaking" — silence it

Install globally:

```bash
ln -s /home/tomas/Repos/speak-aloud/skill ~/.claude/skills/speak-aloud
```
