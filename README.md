# kobo-morning-paper

A self-hosted daily newspaper pipeline. Other programs drop plain-text source files into an inbox; an AI editor turns the combined material into newspaper articles; the existing EPUB builder lays those articles out as a dated paper.

The sources do not need to follow a fixed schema. They can contain full article text, rough notes, dates, lists, plans, URLs, or whatever context the producer has available.

## How it works

1. **Receive sources.** Plain-text files are dropped into the source inbox.
2. **Add optional guidance.** A source can have companion context and expected-output files. Shared editorial skills can be placed in a skills directory.
3. **Build the prompt.** The application sends all source material, source-specific guidance, shared skills, the global context prefix and the expected output instructions to one configured AI model.
4. **Generate articles.** The AI returns structured JSON containing article sections, headlines, standfirsts and body text. The application validates this response and saves article records for the existing newspaper builder.
5. **Build and publish.** The existing builder renders the articles into the dated EPUB and publishes it to configured output folders.
6. **Archive inputs.** Source files and their companion guidance are archived only after the complete build and publishing step succeeds. Files arriving during a run wait for the next edition.

If the AI request, response validation, EPUB build or publishing fails, the source files stay in the inbox for retry.

## Source files

A source is any non-hidden UTF-8 text file in the source inbox. .txt, .md, .text, .json, .jsonl, .urls and other text formats are all treated as text; the application does not require a source schema or try to parse the content.

For example, a producer could write **dinners.txt**:

~~~text
Today: pasta
Tomorrow: curry
Day after tomorrow: soup
~~~

Optional companion files use the same filename stem:

- **dinners.context.txt** — context or a prefix explaining what this source represents.
- **dinners.expected.txt** — what the AI should produce from this particular source.

For example, **dinners.context.txt** could say:

~~~text
These are the household dinner plans for the next few days.
Treat the dates as upcoming plans, not as a report of meals already eaten.
~~~

And **dinners.expected.txt** could say:

~~~text
Turn this into a short newspaper article in a "Coming up" section.
Use a clear heading and list each meal with its actual calendar date.
Keep it concise.
~~~

The AI receives the source and both companion files together. Companion files are archived alongside their source.

### Shared editorial skills

Put reusable skill instructions in .md or .txt files under **KOBO_AI_SKILLS_DIR**. By default this is **<KOBO_DATA_DIR>/skills**.

For example, **data/skills/coming-up.md** might explain how to turn schedules and upcoming dates into a newspaper article. All skill files are included in the prompt for each edition; the model applies the relevant ones.

### Prompt order

The prompt sent to the model contains:

1. Current local date and timezone, so relative dates can be resolved.
2. Global paper context from **KOBO_AI_CONTEXT**.
3. Global expected-output instructions from **KOBO_AI_EXPECTED_OUTPUT**.
4. All shared skill files.
5. For each source: its context prefix, expected-output instructions and raw text.

The built-in system prompt explains the editorial role, prevents unsupported factual invention, and requires a predictable JSON response. **KOBO_AI_SYSTEM_PROMPT** can replace that complete system prompt when a different editorial workflow is wanted.

## AI output contract

The model must return a JSON object with an **articles** array. Each article must contain a headline and body. Optional fields are section, dek/standfirst, source, published date, URL and image.

~~~json
{
  "articles": [
    {
      "section": "Coming up",
      "headline": "Three dinners to look forward to",
      "dek": "A look at the meals planned for the next few evenings.",
      "body": "Thursday, 26 November: Pasta.\n\nFriday, 27 November: Curry.\n\nSaturday, 28 November: Soup.",
      "source": "dinners.txt",
      "published": "2026-11-26",
      "url": null,
      "image": null
    }
  ]
}
~~~

The application converts the plain-text article body into safe HTML paragraphs and stores the result in the existing article cache. The EPUB builder uses the section, headline, standfirst and body when rendering the article. The model can create one article from several sources or several articles from one source.

## AI providers

The AI integration uses a small provider adapter and environment variables. It supports:

- **openai-compatible** — any service exposing the OpenAI Chat Completions API, including Ollama's OpenAI-compatible endpoint, LM Studio, LocalAI, vLLM and llama.cpp server. This is the default provider and does not require an API key.
- **openai** — the OpenAI API.
- **anthropic** — the Anthropic Messages API (Claude).

For local models, set **KOBO_AI_BASE_URL** to the service's OpenAI-compatible /v1 endpoint. For OpenAI and Anthropic, the standard API endpoint is used unless a custom base URL is supplied.

| Variable | Default | Purpose |
|---|---|---|
| **KOBO_AI_PROVIDER** | openai-compatible | openai-compatible, openai or anthropic. |
| **KOBO_AI_BASE_URL** | required for compatible provider | Provider base URL, e.g. http://127.0.0.1:1234/v1. |
| **KOBO_AI_API_KEY** | empty | API key for hosted providers or compatible services that require one. |
| **KOBO_AI_MODEL** | Provider default | Model identifier expected by the selected endpoint. |
| **KOBO_AI_TIMEOUT_SECONDS** | 180 | Request timeout. |
| **KOBO_AI_MAX_TOKENS** | 6000 | Maximum completion tokens. |
| **KOBO_AI_CONTEXT** | built-in general newspaper context | Global context prefix included before the sources. |
| **KOBO_AI_EXPECTED_OUTPUT** | built-in JSON contract | Global output instructions included in the user prompt. |
| **KOBO_AI_SYSTEM_PROMPT** | built-in editorial system prompt | Replaces the complete built-in system prompt. |
| **KOBO_AI_SKILLS_DIR** | <KOBO_DATA_DIR>/skills | Directory containing shared .md and .txt skill instructions. |

Never commit API keys. Supply them through the process environment or a secret manager.

### Example: local OpenAI-compatible model

~~~sh
export KOBO_DATA_DIR="$PWD/data"
export KOBO_AI_PROVIDER=openai-compatible
export KOBO_AI_BASE_URL=http://127.0.0.1:1234/v1
export KOBO_AI_MODEL=your-local-model-id
python scripts/kobo-ingest-build.py
~~~

### Example: OpenAI

~~~sh
export KOBO_AI_PROVIDER=openai
export KOBO_AI_API_KEY=your-api-key
export KOBO_AI_MODEL=gpt-4.1-mini
python scripts/kobo-ingest-build.py
~~~

### Example: Claude

~~~sh
export KOBO_AI_PROVIDER=anthropic
export KOBO_AI_API_KEY=your-api-key
export KOBO_AI_MODEL=claude-sonnet-4-5
python scripts/kobo-ingest-build.py
~~~

The application does not load .env files itself; export variables in the shell, service manager or deployment environment. Docker/Compose integration for the new AI settings is deliberately left for a later step.

## Existing newspaper settings

The existing non-AI settings remain environment-driven:

| Variable | Default | Purpose |
|---|---|---|
| TZ | Europe/London | Local timezone and date handling. |
| KOBO_DATA_DIR | /data | Persistent working directory. |
| KOBO_SOURCE_INGEST_DIR | <KOBO_DATA_DIR>/source-ingest | Source inbox. |
| KOBO_SOURCE_ARCHIVE_DIR | <KOBO_DATA_DIR>/source-archive | Processed source archive. |
| KOBO_OUTPUT_INGEST_DIRS | empty | Comma-separated output folders for the finished EPUB. |
| KOBO_PAPER_TITLE | The Morning Paper | Newspaper masthead. |
| KOBO_PAPER_TAGLINE | All the Reads Worth Your Time | Masthead tagline. |
| KOBO_MAX_AGE_DAYS | 7 | Maximum age of cached articles. |
| KOBO_SCHEDULE_TIME | 03:00 | Built-in scheduler time, 24-hour HH:MM. |
| KOBO_SCHEDULER_RETRY_MINUTES | 15 | Retry interval after a failed scheduled build. |
| KOBO_SCHEDULER_POLL_SECONDS | 20 | Scheduler polling interval. |

## Run locally

~~~sh
git clone https://github.com/joeShuff/kobo-morning-paper.git
cd kobo-morning-paper
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export KOBO_DATA_DIR="$PWD/data"
mkdir -p "$KOBO_DATA_DIR/source-ingest" "$KOBO_DATA_DIR/skills"
# Configure KOBO_AI_PROVIDER / KOBO_AI_BASE_URL / KOBO_AI_MODEL / KOBO_AI_API_KEY
.venv/bin/python scripts/kobo-ingest-build.py
~~~

The generated EPUB is **<KOBO_DATA_DIR>/read-later.epub**. Source files are read from **source-ingest**; successful inputs are moved into **source-archive/YYYY-MM-DD**.

## Tests

~~~sh
.venv/bin/python -m pytest
~~~

## Main components

- **scripts/kobo-ingest-build.py**: source intake, build orchestration and archiving.
- **scripts/kobo_ingest.py**: snapshots text sources and runs the editorial/build stages.
- **scripts/kobo_ai.py**: prompt construction, provider adapters, response validation and article caching.
- **scripts/kobo-digest-build.py**: render, fetch any legacy queued URLs and publish the EPUB.
- **scripts/kobo_config.py**: environment-variable defaults.

## License

MIT
