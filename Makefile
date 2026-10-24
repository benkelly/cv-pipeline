# cv-pipeline: build every version of a CV from one LaTeX source.
#
#   make all       every PDF, variant, cover letter and text format
#   make help      list the targets

TEX_ROOT_FILE = layout.tex

VERSION      ?= $(shell git describe --tags --always 2>/dev/null || echo local)
RELEASE_DATE ?= $(shell date +%F)
PUBLISHED_URL ?=

PDF_TITLE    ?= Curriculum Vitae - $(RELEASE_DATE)
PDF_AUTHOR   ?= Alex Example
PDF_SUBJECT  ?= Alex Example CV
PDF_KEYWORDS ?= CV, Alex Example, Platform Engineer

ifneq ($(PUBLISHED_URL),)
PUBLISHED_LINK_TEX_DEF = \def\showpublishedlinkflag{true}
endif

# TeX definitions passed to every build.
#   $(1) = title suffix, $(2) = extra keywords (start with a comma)
tex_defs = \def\VERSION{$(VERSION)} \def\PDFTITLE{$(PDF_TITLE)$(if $(1), - $(1))} \def\PDFAUTHOR{$(PDF_AUTHOR)} \def\PDFSUBJECT{$(PDF_SUBJECT)$(if $(1), - $(1))} \def\PDFKEYWORDS{$(PDF_KEYWORDS)$(2)} \def\PUBLISHEDURL{$(PUBLISHED_URL)} $(PUBLISHED_LINK_TEX_DEF)

# Compile once.
#   $(1) = engine, $(2) = output name, $(3) = title suffix, $(4) = keywords, $(5) = flags
build_tex = $(1) -jobname=$(2) -interaction=nonstopmode -halt-on-error '$(call tex_defs,$(3),$(4)) $(5) \input{$(TEX_ROOT_FILE)}' >/dev/null || { tail -30 $(2).log; exit 1; }

# The cover letter is on when its \coverletter block is not commented out.
HAS_CL = grep -qE '^[[:space:]]*\\coverletter\{' coverletter.tex

CVONLY  = \def\cvonly{true}
PUBLIC  = \def\showworkinfoflag{true} \def\cvonly{true}
CLONLY  = \def\coverletteronly{true}

ACCESSIBLE        = \def\accessibilityflag{true}
DYSLEXIC          = $(ACCESSIBLE) \def\dyslexicfontflag{true}
INVERTED          = $(ACCESSIBLE) \def\invertcolorsflag{true}
DYSLEXIC_INVERTED = $(DYSLEXIC) \def\invertcolorsflag{true}

.PHONY: all help standard public coverletter accessible dyslexic inverted \
        dyslexic-inverted variants formats index clean

all: standard public accessible dyslexic inverted dyslexic-inverted coverletter variants formats index ## Build everything

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-18s %s\n", $$1, $$2}'

standard: ## cv.pdf
	$(call build_tex,pdflatex,cv,,,$(CVONLY))

public: ## cv_public.pdf, with the public contact details
	$(call build_tex,pdflatex,cv_public,,,$(PUBLIC))

accessible: ## Larger spacing, darker text, clear headings
	$(call build_tex,pdflatex,cv_accessible,Accessible,$(comma) accessible,$(ACCESSIBLE) $(CVONLY))

dyslexic: ## Accessible layout in the OpenDyslexic font (XeLaTeX)
	$(call build_tex,xelatex,cv_dyslexic,Dyslexia-friendly,$(comma) dyslexia-friendly,$(DYSLEXIC) $(CVONLY))

inverted: ## High contrast, yellow on black
	$(call build_tex,pdflatex,cv_inverted,High contrast,$(comma) high-contrast,$(INVERTED) $(CVONLY))

dyslexic-inverted: ## OpenDyslexic, yellow on black
	$(call build_tex,xelatex,cv_dyslexic_inverted,Dyslexia-friendly high contrast,$(comma) dyslexia-friendly$(comma) high-contrast,$(DYSLEXIC_INVERTED) $(CVONLY))

coverletter: ## coverletter.pdf and cv_with_coverletter.pdf, if the letter is on
	@if $(HAS_CL); then \
		$(call build_tex,pdflatex,coverletter,Cover letter,,$(CLONLY)); \
		$(call build_tex,pdflatex,cv_with_coverletter,,,); \
	else echo "Cover letter is commented out, skipping"; fi

variants: ## Print (greyscale), archive (PDF/A) and PNG preview of cv.pdf
	./scripts/variants.sh cv.pdf

formats: ## cv.md, cv.json, cv.html (and cover letter) straight from the LaTeX
	python3 scripts/tex_to_formats.py --source cv.tex --out-base cv --version "$(VERSION)"
	python3 scripts/tex_to_formats.py --source cv.tex --out-base cv_public --public --version "$(VERSION)"
	python3 scripts/tex_to_formats.py --source coverletter.tex --out-base coverletter --version "$(VERSION)"

index: ## index.html linking every output
	python3 scripts/make_index.py --version "$(VERSION)" --date "$(RELEASE_DATE)"

clean: ## Remove build outputs
	rm -f *.aux *.log *.out *.pdf *.png cv*.md cv*.json cv*.html coverletter.md coverletter.json coverletter.html index.html

comma := ,
