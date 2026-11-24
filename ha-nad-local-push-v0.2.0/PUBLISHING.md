# Maintainer checklist

1. Create a GitHub repository named `ha-nad-local-push` (private initially if desired).
2. Replace `YOUR_GITHUB_USERNAME` in `custom_components/nad_push/manifest.json` with the repository owner. Optionally set `codeowners` to your GitHub handle.
3. Review and accept the proposed MIT license before publishing; adjust copyright attribution if appropriate.
4. Upload the extracted repository contents, preserving paths. Do not upload your private Home Assistant files.
5. Back up and test version 0.2.0 on real Home Assistant, preserving your custom source mapping. Check power, mute, volume at low levels, source selection, external changes and reconnect. Check logs and configuration validation.
6. Publish as an experimental pre-release tagged `v0.2.0` only when satisfied with testing; disclose any remaining limitations.

No HACS compatibility or listing is claimed. Do not publish private configuration, logs or screenshots containing secrets.
