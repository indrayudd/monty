# Notes Simulation Specs

## Goal

Build a local simulator that ingests Montessori school notes, streams them at random, and stores each streamed note in a local database sink.

## Assumptions

- The source corpus will live in `notes_streamer/notes`.
- "Ghost database" means a Ghost Build/Postgres database managed through the `ghost` CLI.
- The repository has no existing app framework, so the implementation should be self-contained and runnable with the Python standard library.
- The note files are observation-only; the only in-file metadata is the child's `Name`.

## Note Corpus Requirements

- Create exactly 100 sample notes.
- Keep the balance close to 50 neutral notes and 50 problematic notes.
- Use realistic Montessori-school language and content.
- Make each note much more verbose than the earlier sample set.
- Do not include antecedent, support plan, or other intervention metadata in the note file.
- Each note should include:
  - `Name: <child name>` as the only structured line in the file
  - 2 to 4 long paragraphs of observation text

## Canonical Note File Format

Each `.txt` file should follow this exact structure so the parser can ingest it deterministically:

```text
Name: <full name>

<2-4 verbose paragraphs of body text>
```

## Streamer Requirements

- Read a random note from the corpus.
- Parse the note into a minimal structured record.
- Insert the note into Ghost Build.
- Support repeated streaming in a loop.
- Support a single-run mode for verification.
- Print a concise ingestion log to stdout.

## Database Requirements

- Store ingested notes in Ghost Build/Postgres.
- Create the schema automatically on first run.
- Persist only `name` and `body`, plus an auto-generated primary key.
- Prevent duplicate observations from being inserted more than once.

## Implementation Checklist

- [x] ~~Create the verbose 100-note corpus in `notes_streamer/notes`.~~
- [x] ~~Reduce the parser to the name-plus-observation format.~~
- [x] ~~Update the database sink to use Ghost Build/Postgres.~~
- [x] ~~Update the streamer to log the child name only.~~
- [ ] Verify the streamer can ingest a sample note end to end against Ghost Build.
