#!/usr/bin/env bash
# Publish one interop announcement on stdout, for a sibling plugin to react to.
#
#   announce.sh content.routed tier=maintainer path=docs/release.md title="Releasing" reason="..."
#   -> codes.bridgeai.masthead/content.routed {"tier":"maintainer","path":"docs/release.md","title":"Releasing","reason":"..."}
#
# The canonical guide is the suite's interop contract, which owns the grammar,
# the body rules, and the reasoning behind both:
# https://github.com/chris-peterson/claude-marketplace/blob/main/authoring/plugin-contract.md
#
# Ported from anchor's scripts/announce.sh; only the plugin segment differs. The
# plugin segment is fixed rather than an argument: a plugin announces facts it
# caused, never one it observed a sibling cause.
#
# The body is built by jq rather than interpolated, which is what lets a value
# carry a space, a quote, or a newline without breaking the one-line contract:
# `jq -c` escapes those inside the string instead of emitting them.
#
# Exits 0 on every path, malformed calls included: see the contract's
# publishing rules. This runs after the work it describes, so turning an
# operation that succeeded into a tool call that failed is the one outcome it
# must never produce.

set -uo pipefail

readonly PLUGIN=masthead

key="${1:-}"
[[ $# -gt 0 ]] && shift

if [[ ! $key =~ ^[a-z0-9]+\.[a-z0-9]+$ ]]; then
  echo "announce.sh: expected <entity>.<event> in lowercase, got: ${key:-<empty>}" >&2
  exit 0
fi

# Collected as jq --arg pairs. `${jq_args[@]+...}` rather than a bare expansion:
# under `set -u`, bash 3.2 treats an empty array as unbound.
jq_args=()
for field in "$@"; do
  if [[ ! $field =~ ^[a-z][a-z0-9_]*= ]]; then
    echo "announce.sh: field must be lowercase name=value, got: $field" >&2
    exit 0
  fi
  jq_args+=(--arg "${field%%=*}" "${field#*=}")
done

# A missing jq lands here as a non-zero from the encode itself, which this
# catches like any other failure to build a body.
if ! body=$(jq -cn ${jq_args[@]+"${jq_args[@]}"} '$ARGS.named' 2>/dev/null); then
  echo "announce.sh: could not encode the body, so the announcement was not made" >&2
  exit 0
fi

printf '%s %s\n' "codes.bridgeai.${PLUGIN}/${key}" "$body"
exit 0
