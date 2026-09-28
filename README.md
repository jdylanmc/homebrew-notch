# Notch Pocket Homebrew tap

Owned distribution repository for [Notch Pocket](https://github.com/jdylanmc/notch).
The **0.1.0** cask uses the Developer ID-signed, notarized and stapled
[Notch Pocket release](https://github.com/jdylanmc/notch/releases/tag/notch-pocket-v0.1.0),
not the upstream application.

```bash
brew install --cask jdylanmc/notch/notch-pocket
```

The cask points only to the owned release's `notch-pocket-0.1.0.dmg`, with
the SHA-256 of its final signed, notarized and stapled bytes. It installs
`notch-pocket.app` on macOS Sonoma (14) or later. No quarantine removal,
Gatekeeper bypass, automatic app launch or user-data removal belongs in the cask.

## Update and acceptance workflow

The application release workflow opens a cask-update PR in this repository.
Publish only product-qualified Notch Pocket tags; inherited upstream tags are
not release inputs for this tap.
Review the version, product-qualified tag, asset URL and final checksum. CI
checks the exact reviewed cask shape, downloads and hashes the public DMG, and
runs Homebrew's strict online cask audit before the PR is merged. A checksum
proves artifact identity, not notarization by itself; native signing, ticket and
Gatekeeper evidence belongs to the corresponding application release.

CI registers the exact checkout as a temporary tap on its ephemeral runner,
verifies the cloned commit and cask contents match, then audits
`jdylanmc/notch/notch-pocket` by name. File-path audit syntax is no longer
supported by Homebrew. The launcher refuses pre-existing taps and local
execution; it never installs or launches the application.

The initial infrastructure PR has no cask, so download/audit steps explicitly
skip and report bootstrap status. Recursive policy checks reject other Ruby
definitions, including nested casks and formulae; a published cask cannot be
removed to regain bootstrap status. Once a cask exists those gates run on every
PR and main-branch push. No synthetic checksum is committed as a product cask.

The repository owner is `@jdylanmc`. Review infrastructure changes as well as
cask content: PRs run their proposed workflow and tests, so a green check is
not independent approval of changes to those gates.

The owner will verify installation, launch, permissions and coexistence on
additional Macs **after publication**. That confirmation closes the remaining
distribution acceptance under [notch #9](https://github.com/jdylanmc/notch/issues/9);
it is not a pre-publication gate.

## Local policy checks

```bash
python3 -B -m unittest discover -s tests
```

Once a cask is present, validate its structure, or download/hash the release
without installing it:

```bash
python3 -B scripts/check_cask.py
python3 -B scripts/check_cask.py --online
```

Tests use synthetic bytes and never install an application. A missing cask is an
explicit error for the checker, not a claim that distribution is ready.
