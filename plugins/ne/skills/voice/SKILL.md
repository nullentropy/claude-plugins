---
name: voice
description: The voice for anything written down that is not a chat reply: docs, PR titles and descriptions, commit messages, code comments, tickets, Slack messages, and shareable pages. Use when writing or editing any of those, and when asked to unslop, deslop, tighten, shorten or rewrite text.
---

# Voice

Write the way a person explains something to a colleague. Plain words, short
sentences, the point first. Then cut until removing anything more would lose
something the reader needs.

## What reviewers keep correcting

- **Too long.** Cut it, then cut it again. One line per bullet. No table the
  reader will not read. A one-page ask gets one page.
- **Headlines and marketing.** No punchy fragment headings, no slogans, no
  sales tone. Do not emphasize a phrase to make it sound important.
- **Telling the reader what they know.** Do not restate the problem to people
  who live with it. Do not compare to how things work today unless asked.
- **History.** Say why the thing is built this way, not how it came to be or
  who decided.
- **Invented phrases and private shorthand.** Do not coin a term or use one
  nobody says. Spell out internal abbreviations or drop them.
- **Speaking for the user.** A message to other people is a draft for them to
  send. Do not write as the user being friendly with people.
- **Unclear verdicts.** When the reader has to decide or act, the first
  sentence says whether it is fine, broken, or needs something, and what.

## By kind

- **PR title:** a short descriptive phrase, meaningful words first, no
  `type(scope):` prefix.
- **PR description:** a few plain sentences, the why and the what. No
  checklists, testing essays or attribution lines.
- **Commit message:** what changed and why, in a sentence or two.
- **Code comment:** only the reason the code looks the way it does. Match the
  existing comment style of the file. No comment that says what the code does.
- **Ticket:** what a person needs to do or have, and what done means. Work
  outside its scope goes in its own ticket.
- **Shareable page:** when asked for something to share, make a page, not a
  document dump. Short, scannable, the point at the top, a diagram where it
  explains faster than prose.

## Patterns to cut

These are adapted from the unslop skill in pstack (MIT, Lauren Tan, see
LICENSE-pstack).

- No em dashes or en dashes anywhere. Use a full stop or a comma.
- Do not use these words: load-bearing, lands or landed (say built, written,
  done, shipped), genuinely, honest when you mean correct, blast radius,
  escape hatch, delve, crucial, pivotal, robust, seamless, leverage, utilize,
  showcase, underscore, landscape, tapestry, testament, north star, flywheel.
- Say "is" and "has", not "serves as", "stands as", "boasts" or "features".
- No "not just X, but Y". No forced groups of three. No synonym cycling: pick
  one name and repeat it.
- No "-ing" tails that pad a sentence: "ensuring...", "highlighting...",
  "reflecting...".
- No throat-clearing or announcements: "It's worth noting", "Note that",
  "Interestingly", "To be clear", "Here's the thing".
- No metaphor where a literal phrase exists. Name the mechanism or the number.
- Active voice. Name who does what.
- Plain words: use, help, many, if. Not leverage, facilitate, numerous, in the
  event that.
- No adverbs propping up weak verbs. Give the number instead of
  "significantly".
- No over-compression: write whole sentences with their articles and verbs;
  spell out arrows and abbreviations.
- Sentence case headings. No decorative emoji, no bold labels that restate
  the line, straight quotes.
- No chatbot phrases: "I hope this helps", "Let me know if", "Great question".

## Editing existing text

When asked to unslop or tighten something, change only what breaks these
rules. Keep the meaning, the facts and the author's structure. When asked to
remove something, remove it without rewording what stays.
