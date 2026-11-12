# Wiring the deploy into existing CI

Read this when the repo already has a CI workflow, so the scaffold script
declined to write a standalone one. It covers GitHub Actions, GitLab CI, and
the one-time Pages setup each host needs.

The script writes a standalone CI file only when none exists. When a workflow is
already there it prints a note and leaves the wiring to you: matching the
pipeline's conventions, its change detection, and its action versions is
judgment, not a template.

## GitHub

Look for `.github/workflows/ci.yml` or similar. The shape below assumes a
`release-gate` job that runs `dorny/paths-filter`; adapt it to whatever gating
the workflow already does.

1. **Add a `force_publish_docs` input** to the `workflow_dispatch` trigger:

   ```yaml
   workflow_dispatch:
     inputs:
       force_publish_docs:
         description: 'Force publish docs (bypass change detection)'
         type: boolean
         default: false
   ```

2. **Add docs change detection** to the gate job's paths filter and outputs:

   ```yaml
   outputs:
     changes_in_docs: ${{ steps.changes.outputs.docs }}
   # ...in the filters block:
   filters: |
     docs:
       - 'docs/**'
   ```

3. **Add a `publish-docs` job** that runs after the gate:

   ```yaml
   publish-docs:
     name: Publish documentation
     needs: release-gate
     if: needs.release-gate.outputs.changes_in_docs == 'true' || inputs.force_publish_docs == true
     runs-on: ubuntu-latest
     permissions:
       pages: write
       id-token: write
     environment:
       name: github-pages
       url: ${{ steps.deployment.outputs.page_url }}

     steps:
       - uses: actions/checkout@v6

       - name: Setup Pages
         uses: actions/configure-pages@v5

       - name: Upload artifact
         uses: actions/upload-pages-artifact@v4
         with:
           path: docs

       - name: Deploy to GitHub Pages
         id: deployment
         uses: actions/deploy-pages@v4
   ```

Match the action versions and patterns the existing workflow already uses. If
the repo is spec-driven, copy the spec into `docs/` before the upload step (see
[spec-driven repos](docsify.md#spec-driven-repos)).

## GitLab

If `.gitlab-ci.yml` already exists, append the `pages:` job and confirm a
`deploy` stage is declared:

```yaml
pages:
  stage: deploy
  script:
    - mkdir -p public
    - cp -r docs/* public/
  pages: true
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

## One-time Pages setup

Once CI lands, tell the user about the setting each host needs (the script
prints the URL for GitHub):

- **GitHub:** Settings > Pages > Build and deployment > Source > GitHub Actions.
- **GitLab:** Settings > Pages. It is usually on by default once a `pages:` job
  has run.
