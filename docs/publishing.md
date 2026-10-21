# GitHub publication

Author: [kristoferUA](https://github.com/kristoferUA) · Competition: Securinets · License: MIT.

## Repository contents

Use the contents of `Securinets-old-calculator-github.zip` as the repository root. The English writeup is `README.md`; the Ukrainian version is `README.uk.md`. Docker commands run from the same root.

The complete bundle adds the prebuilt image under `release-assets/`. Its Git ignore rules keep the image as a release asset while retaining its directory README. Recorded public protocol evidence in `reference/` is included in the Git tree.

## Commit and push

Target repository: [kristoferUA/Securinets-CTF-2026-Old-Calculator-writeup](https://github.com/kristoferUA/Securinets-CTF-2026-Old-Calculator-writeup). From the prepared repository folder:

```bash
git init -b main
git add .
git commit -m "Add Old Calculator writeup and local Linux instance"
git remote add origin https://github.com/kristoferUA/Securinets-CTF-2026-Old-Calculator-writeup.git
git push -u origin main
```

If using another repository name or an existing writeups repository, use that repository's remote and folder layout.

## Publish the Linux image

The initial image is published in [Release v1.0.0](https://github.com/kristoferUA/Securinets-CTF-2026-Old-Calculator-writeup/releases/tag/v1.0.0). For a subsequent version, create a new GitHub Release and attach these files from `release-assets/` in the complete bundle:

```text
old-calculator-linux-amd64.tar.gz
old-calculator-linux-amd64.tar.gz.sha256
```

Suggested release title: `Old Calculator — writeup and local Linux instance`.

Suggested description:

```text
Securinets Old Calculator by kristoferUA.
Includes English and Ukrainian writeups, a local solver, the reconstructed TCP service,
and random/recorded 16-round scenarios. The attached image targets linux/amd64.
Use the repository Dockerfile to build on another CPU architecture.
```

The root `SHA256SUMS.txt` covers the repository source files. The separate image checksum covers the prebuilt archive.

## Українською

Розпакуй архів для GitHub і використовуй його вміст як корінь репозиторію. Вище вказана адреса цільового репозиторію `kristoferUA/Securinets-CTF-2026-Old-Calculator-writeup` та команди створення й відправлення коміту.

Готовий Linux-образ і його `.sha256` із повного комплекту додай до GitHub Release. У Git зберігаються код, обидва врайтапи, сценарій і докази протоколу; для великого готового образу налаштована папка `release-assets/`.

Ця підготовка створює локальні файли репозиторію та релізу. Публікація виконується наведеними командами у вибраному акаунті.
