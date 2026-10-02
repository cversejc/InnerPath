# Bundled font licenses

This project bundles font files for local rendering so the visual design does
not depend on fonts installed on the visitor's device.

## Source Han Sans CN

- Upstream: https://github.com/adobe-fonts/source-han-sans
- Files: `source-han-sans-cn-regular.woff2`, `source-han-sans-cn-bold.woff2`
- License: SIL Open Font License 1.1, see `OFL-SourceHanSans.txt`

## Source Han Serif CN

- Upstream: https://github.com/adobe-fonts/source-han-serif
- Files: `source-han-serif-cn-regular.woff2`, `source-han-serif-cn-bold.woff2`
- License: SIL Open Font License 1.1, see `OFL-SourceHanSerif.txt`

The WOFF2 files in this directory are local web-font subsets generated from the
official upstream releases. No runtime font request is made to a third party.

Each subset keeps the GB2312 character set, ASCII, fullwidth forms and the
punctuation used by the interface, plus every character that appears in
`src/` and `index.html`. Keeping two families and two weights per family keeps
the bundled font payload below 8 MB instead of shipping a third accent family.
