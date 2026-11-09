---
name: mentat
description: Discovery. Agree with the user how a feature should work before building it. Reads the ticket and the code, writes down what exists today, and asks the user every question about behavior, invariants and edge cases that the ticket, code and docs do not settle. Use before planning or building a feature, user story, enhancement or anything that says what a person should be able to do; when starting work on a ticket that is not a plain bug; and whenever the discovery gate blocks an edit.
---

# Mentat

The user decides how the product behaves. Your job here is to find every
decision the work depends on and put it to them, not to make it for them. An
invariant you assume is a bug they find in review.

Discovery applies to a feature, a user story, an enhancement, or anything that
describes what a person should be able to do. It does not apply to a bug with a
clear reproduction and stated expected behavior, a refactor that changes no
behavior, or a docs, test or config change. For those, record a skip with
`scripts/discovery.sh skip "<reason>"` from inside the repository and tell the
user the reason in one line.

## Steps

1. **Read the ask.** For a ticket, `gh issue view <n> --comments`, and any issue
   it links to. Otherwise the user's message.

2. **Read what exists.** Find where this behavior lives today: the code paths,
   the data it reads and writes, the docs or specs that describe it, and the
   tests that pin it. Note each fact with `file:line`. Delegate wide searches to
   a cheap subagent and keep the conclusions.

3. **Find the decisions.** List every question about behavior that the ticket,
   the code and the docs leave open. Do not ask what the code already answers.
   Go through these and keep the ones that apply:
   - Who can see it, who can do it, and who is told when it happens.
   - Existing data: what happens to rows, accounts or settings that already
     exist, and whether anything needs moving.
   - States: empty, partial, failed, retried, and two people acting at once.
   - What must always hold true, and what must never happen.
   - How it is undone, and what is kept as history.
   - Limits and scale.
   - What is out of scope, so it does not hold the ticket open.

4. **Write the record.** Get its path with `scripts/discovery.sh path` and write
   it in this shape. The first line is what the edit gate reads.

   ```
   status: open
   ticket: <link, or "none">

   ## Ask
   <one paragraph in your own words>

   ## Today
   <facts with file:line>

   ## Questions
   1. <question> Options: <a>, <b>. Recommended: <a>, because <reason>.

   ## Agreed behavior
   ```

5. **Ask.** Put the questions to the user with AskUserQuestion, up to four per
   call, recommended option first. Each question names the decision and why it
   matters in a sentence. Record each answer under its question. When an answer
   raises a new question, add it and ask it.

6. **Agree.** When every question is answered, write the agreed behavior as
   plain statements of what the product does, one per line. These are the
   invariants the build and its tests hold to. Set the first line to
   `status: agreed`, show the user the agreed behavior, and ask whether to post
   it on the ticket.

7. **While building.** If a new question about behavior comes up, set the
   status back to `open`, add the question, and ask it. Edits stay blocked
   until it is answered.
