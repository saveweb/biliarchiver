# biliarchiver

> 基于 bilix 的 BiliBili 存档工具

## Install

```bash
pip install biliarchiver
```

## Usage

```bash
biliarchiver --help
```

Follow these steps to start archiving:

1. Initialize a new workspace in current working directory:
```bash
biliarchiver init
```
2. Provide cookies and tokens following instructions:
```bash
biliarchiver auth
```
3. Download videos from BiliBili:
```bash
biliarchiver down --bvids BVXXXXXXXXX
```
- This command also accepts a list of BVIDs or path to a file. Details can be found in `biliarchiver down --help`.
4. Upload videos to Internet Archive:
```bash
biliarchiver up --bvids BVXXXXXXXXX
```
- This command also accepts a list of BVIDs or path to a file. Details can be found in `biliarchiver up --help`.

## Develop

### Install

Please use poetry to install dependencies:

```sh
poetry install
```

### Run

```sh
poetry run biliarchiver --help
```

### Lint

```sh
poetry run ruff check .
```

### i18n

Generate `biliarchiver.pot`:

```sh
find biliarchiver/ -name '*.py' | xargs xgettext -d base -o biliarchiver/locales/biliarchiver.pot
```

Add a new language:

```sh
msginit -i biliarchiver/locales/biliarchiver.pot -o en.po -l en
```

Update a language:

```sh
pnpx gpt-po sync --po biliarchiver/locales/en/LC_MESSAGES/biliarchiver.po --pot biliarchiver/locales/biliarchiver.pot
```

Build a language:

```sh
msgfmt biliarchiver/locales/en/LC_MESSAGES/biliarchiver.po -o biliarchiver/locales/en/LC_MESSAGES/biliarchiver.mo
```
