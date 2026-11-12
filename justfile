shipyard := "uvx --from 'git+https://github.com/chris-peterson/shipyard@v2' shipyard"

# What this is, and every recipe there is
[private]
default:
    @echo ""
    @echo "  masthead stands up a docsify site for a repo and keeps it deploying."
    @echo ""
    @just --list --unsorted --list-prefix '    ' --list-heading ''

# Open an interactive session with the local plugin loaded
[group('try it out')]
try:
    claude --plugin-dir .

# Run the script tests (bootstrap scaffold, announcements)
[group('check your work')]
test:
    python3 -m unittest discover -s tests

# Regenerate the artifacts and list what the projection job would commit
[group('check your work')]
check-generated:
    {{shipyard}} generate
    git --no-pager diff --stat

# Check the plugin the way the projection job does (needs `claude` on PATH)
[group('check your work')]
validate:
    {{shipyard}} validate

# Render the docs site into docs/: skill pages, the spec, and index.html
[group('docs')]
docs:
    {{shipyard}} build-docs

# Preview the docs site locally
[group('docs')]
preview-docs: docs
    npx docsify-cli serve docs --open
