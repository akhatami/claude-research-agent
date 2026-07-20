#!/usr/bin/env python3
"""Build a throwaway corpus that exercises the /sync refresh path.

The corpus holds one paper, ingested from its arXiv preprint. Sitting
uningested in papers/ is the camera-ready of that same paper: same arXiv id,
different bytes, one extra page, a real venue, and a headline number that moved
from page 3 to page 4.

A correct /sync classifies the camera-ready as a *refresh* of the held entry.
A /sync that only knows "new vs not-new" mints a second slug for it, then the
dedupe check quarantines it into _duplicates/ and the stale text survives.

Two layouts:

  side-by-side (default)  the camera-ready arrives under its own filename, so
                          the preprint is still on disk to compare against.
  in-place                the user overwrote papers/<slug>.pdf with the
                          camera-ready bytes. Nothing is left to compare
                          against: the only signal is that the file at a held
                          entry's own path no longer matches its file_hash.

Usage: make_fixture_corpus.py <dest-dir> [side-by-side|in-place]
"""

import os
import shutil
import subprocess
import sys
import textwrap

PREPRINT_PAGES = [
    [
        "SimCLR v3: Stronger Contrastive Representations",
        "",
        "Alice Doe, Bob Roe",
        "Institute for Representation Learning",
        "",
        "arXiv:2103.04567v1  [cs.LG]  8 Mar 2021",
        "",
        "Abstract",
        "We present SimCLR v3, a contrastive framework that improves",
        "linear-probe accuracy on ImageNet over prior contrastive methods.",
    ],
    [
        "1  Introduction",
        "",
        "Contrastive learning has become the dominant paradigm for",
        "self-supervised visual representation learning.",
    ],
    [
        "4  Results",
        "",
        "On ImageNet, SimCLR v3 reaches 76.1% top-1 accuracy under the",
        "standard linear evaluation protocol, a 2.3 point gain over the",
        "strongest prior contrastive baseline.",
    ],
    [
        "References",
        "",
        "[1] Lee, K. A Large-Scale Benchmark for Representation Learning. 2019.",
        "[2] Chen, T. A Simple Framework for Contrastive Learning. 2020.",
    ],
]

# Camera-ready: an added Related Work page pushes Results from p.3 to p.4, and
# the headline number is corrected upward after a training-schedule fix.
CAMERA_READY_PAGES = [
    [
        "SimCLR v3: Stronger Contrastive Representations",
        "",
        "Alice Doe, Bob Roe",
        "Institute for Representation Learning",
        "",
        "Advances in Neural Information Processing Systems 34 (NeurIPS 2021)",
        "arXiv:2103.04567v2  [cs.LG]  2 Nov 2021",
        "",
        "Abstract",
        "We present SimCLR v3, a contrastive framework that improves",
        "linear-probe accuracy on ImageNet over prior contrastive methods.",
    ],
    [
        "1  Introduction",
        "",
        "Contrastive learning has become the dominant paradigm for",
        "self-supervised visual representation learning.",
    ],
    [
        "2  Related Work",
        "",
        "This section was added during camera-ready revision at the request",
        "of Reviewer 2, and situates our objective against House-GAN and",
        "the broader family of contrastive objectives.",
    ],
    [
        "4  Results",
        "",
        "On ImageNet, SimCLR v3 reaches 76.8% top-1 accuracy under the",
        "standard linear evaluation protocol, a 3.0 point gain over the",
        "strongest prior contrastive baseline. This corrects the 76.1%",
        "reported in the preprint, which used a truncated LR schedule.",
    ],
    [
        "References",
        "",
        "[1] Lee, K. A Large-Scale Benchmark for Representation Learning. 2019.",
        "[2] Chen, T. A Simple Framework for Contrastive Learning. 2020.",
    ],
]

INDEX_YAML = """\
- slug: 2021-doe-simclr-v3
  title: "SimCLR v3: Stronger Contrastive Representations"
  authors: ["Doe, Alice", "Roe, Bob"]
  year: 2021
  venue: null
  ids: {doi: null, arxiv: "2103.04567"}
  original_filename: "2103.04567v1.pdf"
  file_hash: sha256:%s
  summary: "A contrastive framework reporting improved ImageNet linear-probe accuracy."
  tags: [contrastive-learning, imagenet, self-supervised]
  status: metadata-unverified
"""

CARD = """\
# SimCLR v3: Stronger Contrastive Representations [2021-doe-simclr-v3]

**Problem:** contrastive objectives underperform supervised pretraining on ImageNet.
**Method:** a contrastive framework with a revised projection head and augmentation stack.
**Datasets/benchmarks:** ImageNet, linear evaluation protocol.
**Key results:** the headline linear-probe number:
> "On ImageNet, SimCLR v3 reaches 76.1% top-1 accuracy under the" (p. 3)
**Limitations:** preprint; venue unverified.
**Relations:** none recorded.
"""


def ps_escape(line):
    return line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf(pages, dest):
    """Render text pages to a PDF with a real text layer, via PostScript."""
    chunks = ["%!PS-Adobe-3.0"]
    for page in pages:
        chunks.append("/Times-Roman findfont 11 scalefont setfont")
        y = 720
        for line in page:
            chunks.append("72 %d moveto (%s) show" % (y, ps_escape(line)))
            y -= 16
        chunks.append("showpage")
    ps = "\n".join(chunks) + "\n"

    ps_path = dest + ".ps"
    with open(ps_path, "w") as fh:
        fh.write(ps)
    subprocess.run(["ps2pdf", ps_path, dest], check=True)
    os.remove(ps_path)


def sha256(path):
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def extract_text(pdf_path):
    out = subprocess.run(
        ["pdftotext", "-layout", pdf_path, "-"], check=True, capture_output=True
    )
    return out.stdout.decode("utf-8")


def main(argv):
    if len(argv) not in (2, 3):
        print(
            "usage: make_fixture_corpus.py <dest-dir> [side-by-side|in-place]",
            file=sys.stderr,
        )
        return 2

    root = os.path.abspath(argv[1])
    layout = argv[2] if len(argv) == 3 else "side-by-side"
    if layout not in ("side-by-side", "in-place"):
        print("unknown layout: %s" % layout, file=sys.stderr)
        return 2

    if os.path.exists(root):
        shutil.rmtree(root)

    corpus = os.path.join(root, "corpora", "testcorpus")
    for sub in ("papers", "text", "notes", "_duplicates", "synthesis"):
        os.makedirs(os.path.join(corpus, sub))
    os.makedirs(os.path.join(root, "scripts"))

    held = os.path.join(corpus, "papers", "2021-doe-simclr-v3.pdf")
    scratch_preprint = os.path.join(root, ".preprint.pdf")
    write_pdf(PREPRINT_PAGES, scratch_preprint)

    # index.yaml, text/ and notes/ always describe the preprint — that is what
    # was ingested. The layouts differ only in what sits in papers/ now.
    with open(os.path.join(corpus, "text", "2021-doe-simclr-v3.md"), "w") as fh:
        fh.write(extract_text(scratch_preprint))
    with open(os.path.join(corpus, "notes", "2021-doe-simclr-v3.md"), "w") as fh:
        fh.write(CARD)
    with open(os.path.join(corpus, "index.yaml"), "w") as fh:
        fh.write(INDEX_YAML % sha256(scratch_preprint))
    with open(os.path.join(corpus, "refs.yaml"), "w") as fh:
        fh.write("[]\n")

    if layout == "side-by-side":
        shutil.move(scratch_preprint, held)
        write_pdf(
            CAMERA_READY_PAGES,
            os.path.join(corpus, "papers", "doe_neurips_camera_ready.pdf"),
        )
    else:
        # The preprint is gone. papers/<slug>.pdf now holds camera-ready bytes.
        os.remove(scratch_preprint)
        write_pdf(CAMERA_READY_PAGES, held)

    here = os.path.dirname(os.path.abspath(__file__))
    shutil.copy(
        os.path.join(here, "..", "generate_views.py"),
        os.path.join(root, "scripts", "generate_views.py"),
    )
    with open(os.path.join(root, ".active-corpus"), "w") as fh:
        fh.write("testcorpus\n")

    print(root)
    if layout == "side-by-side":
        print(
            textwrap.dedent(
                """\
                layout   : side-by-side
                held     : papers/2021-doe-simclr-v3.pdf        (preprint, 76.1%, p.3, no venue)
                incoming : papers/doe_neurips_camera_ready.pdf  (camera-ready, 76.8%, p.4, NeurIPS 2021)
                signal   : shared arXiv id 2103.04567 -> same work -> REFRESH
                """
            )
        )
    else:
        print(
            textwrap.dedent(
                """\
                layout   : in-place
                papers/2021-doe-simclr-v3.pdf now holds CAMERA-READY bytes (76.8%, p.4)
                index.yaml / text/ / notes/ still describe the PREPRINT (76.1%, p.3)
                signal   : file at a held entry's own path no longer matches its file_hash -> REFRESH
                """
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
