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

## Alibaba PuHuiTi 3.0

- Upstream: https://fonts.alibabagroup.com/
- Files: `alibaba-puhuiti-3-regular.woff2`, `alibaba-puhuiti-3-bold.woff2`
- Usage: the official product description states that Alibaba PuHuiTi is a
  permanently free genuine font family for global commercial use.
- Terms and legal statement:
  - https://www.yuque.com/yiguang-wkqc2/hgpff0/nus9wiinq4aeiegy
  - https://www.yuque.com/yiguang-wkqc2/hgpff0/mlordz0p7q9nmrfw

The WOFF2 files in this directory are local web-font subsets generated from the
official upstream releases. No runtime font request is made to a third party.

Each subset keeps the GB2312 character set, ASCII, fullwidth forms and the
punctuation used by the interface, plus every character that appears in
`src/` and `index.html`. Subsetting keeps the six files at roughly 9.7 MB
instead of the ~41 MB of the unsubset upstream releases, which matters on the
mobile layouts.
