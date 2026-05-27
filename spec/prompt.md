Produce a structured markdown transcript file. Output ONLY the markdown, no preamble. Use this exact structure:
```
---
type: transcript
topic: [descriptive topic derived from content]
tags: [relevant, comma, separated, tags]
interview-date: [year if detectable, else YYYY]
transcription: whisper-base
source: https://www.youtube.com/watch?v=VIDEO_ID
context: [1-2 sentence summary: who is speaking, setting, and purpose]
---

# [Title derived from content]

## [Section Heading]
[content]

Cleaning rules:
- Remove filler words: uh, um, ah, you know, like (when used as filler), stutters and false starts
- Fix obvious Whisper mishearings using surrounding context (e.g. proper nouns, technical terms)
- Group continuous speech into logical thematic sections with ## headings
- Do NOT paraphrase — preserve the speaker's exact meaning and vocabulary
- Do NOT summarise — this is a cleaned transcript, not a summary
- Remove duplicate sentences caused by Whisper looping artifacts"
```