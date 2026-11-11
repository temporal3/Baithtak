# baithak · بیٹھک

The complete poems of temporal: haiku and Urdu verse, searchable, with a loom that weaves new poems from the poet's own lines. Everything is posted first at [baithak.blogspot.com](https://baithak.blogspot.com).

## How the page gets its poems

1. `poems.json` is a saved copy of every poem, in full. A GitHub Action (`.github/workflows/snapshot.yml`) refreshes it every day, or on demand from the **Actions** tab (**Save every poem**, then **Run workflow**).
2. On every visit, `index.html` loads `poems.json` first, so the archive appears at once and stays complete even if the blog is slow.
3. It then reads the live blog feed to pick up anything newer than the last snapshot.

Poems are shown whole, with the title and the date heading laid out the way the blog prints them. If the blog only hands over the opening of a poem, the card says so and links to the full text.

## Files

- `index.html` is the whole site (no build step).
- `poems.json` is the saved copy of the poems (created by the Action).
- `scripts/fetch_poems.py` builds `poems.json` (Python standard library only).
- `Index.html` is an older alternate page. Its name differs from `index.html` only by a capital letter, which GitHub Pages treats as a different file; consider removing it.

To rebuild `poems.json` by hand: `python3 scripts/fetch_poems.py`
