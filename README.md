# cv-pipeline

One LaTeX file. Every version of your CV, built and published by CI.

**Live demo: [benkelly.github.io/cv-pipeline](https://benkelly.github.io/cv-pipeline/)**

This is a public, cut-down copy of the pipeline I use for my own CV. The CV in
here is made up: Taylor Template doesn't exist. Swap in your own content and it
all still works.

## What it builds

From `cv.tex` and `layout.tex`, one `make all` gives you:

| File | What it is |
| --- | --- |
| `cv.pdf` | The standard CV |
| `cv_public.pdf` | Public contact details, no phone number |
| `cv_accessible.pdf` | Larger line spacing, darker text, clear heading bars |
| `cv_dyslexic.pdf` | The accessible layout in the [OpenDyslexic](https://opendyslexic.org) font |
| `cv_inverted.pdf` | High contrast, yellow on black |
| `cv_dyslexic_inverted.pdf` | OpenDyslexic, yellow on black |
| `coverletter.pdf`, `cv_with_coverletter.pdf` | Only if the cover letter is turned on |
| `cv_print.pdf`, `cv_archive.pdf`, `cv_preview.png` | Greyscale, PDF/A and a PNG preview |
| `cv.md`, `cv.json`, `cv.html` | Generated straight from the LaTeX, for software and AI tools |
| `index.html` | A page linking all of the above |

## Why

I'm dyslexic. Editing a CV in Word, with formatting that moves and five copies
called `cv_final_v3`, was never going to work for me. Text in git is easier: change
a line, see the diff, let the computer do the rest.

It also means the CV can be readable by more people. The accessible versions
aren't just a font swap. Each one needed its own layout fixes.

And a lot of CVs are now read by software first. Two-column PDFs come out
scrambled when a tool extracts the text, so `scripts/tex_to_formats.py` reads
the LaTeX directly and writes clean Markdown, JSON and HTML in the right order.

## Branches are applications

Make a branch for each job you apply for, and open a pull request:

```bash
git checkout -b example-corp/platform-engineer
# tailor cv.tex and coverletter.tex for the role
git commit -am "Tailor CV for Example Corp"
git push -u origin example-corp/platform-engineer
```

GitHub Actions builds every version, publishes them to
`<your pages site>/<branch>/<date>/`, and comments the links on the pull
request so you can check everything before you send it. Merging to `main`
updates the site root.

## Use it for your own CV

1. Click **Use this template**, or fork the repo.
2. Edit your name and contact details in `layout.tex` (`\namesection` and
   `\contactinfo`). The public version uses the first branch of the
   `\ifthenelse{\boolean{showworkinfo}}` block.
3. Replace the content of `cv.tex`. Each entry is
   `\cvsection[note]{Section}{Heading}{Body}`. Leave `Section` empty for a
   follow-on entry, like a second job.
4. Turn the cover letter on or off by commenting out the `\coverletter` block in
   `coverletter.tex`.
5. Optional: add a `static/sig.png` signature for the cover letter.
6. In **Settings → Pages**, set the source to the `gh-pages` branch after the
   first build.

## Build locally

You need a TeX Live install with XeLaTeX, Ghostscript and Python 3.

```bash
# Debian / Ubuntu
sudo apt-get install texlive-latex-extra texlive-fonts-recommended texlive-xetex ghostscript
# macOS
brew install --cask mactex && brew install ghostscript

make all     # everything
make help    # every target
make clean
```

## Layout

```
cv.tex                 CV content
coverletter.tex        optional cover letter
layout.tex             the template, and the flags each version switches on
Makefile               one target per version
scripts/
  tex_to_formats.py    LaTeX to Markdown, JSON and HTML (standard library only)
  variants.sh          print, archive and preview with Ghostscript
  make_index.py        the index page
fonts/                 OpenDyslexic (SIL Open Font License)
.github/workflows/     build on every PR, publish to GitHub Pages
```

## Licence

Code is MIT. The OpenDyslexic fonts are under the SIL Open Font License, in
[`fonts/OFL.txt`](fonts/OFL.txt).
