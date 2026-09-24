"""Importers that pull your writing out of common exports into samples/<source>/.

Every importer is stdlib-only so it runs on the machine that holds the data
(your Mac for iMessage, wherever you unzipped a Takeout) with no installs.

    python -m myvoice.importers.takeout_docs  ~/Downloads/Takeout
    python -m myvoice.importers.imessage       # reads ~/Library/Messages/chat.db
    python -m myvoice.importers.claude_export  ~/Downloads/data-2026-xx-xx/conversations.json
    python -m myvoice.importers.claude_code    # reads ~/.claude/projects
    python -m myvoice.importers.mbox           ~/Downloads/Takeout/Mail/Sent.mbox --me you@example.com
"""
