"""
MeSH -> Dify Knowledge Base import file.

Converts NLM's MeSH Descriptors XML (desc2026.gz) into a text corpus that
imports cleanly into a Dify knowledge base, replacing the FAISS index
(mesh_index.faiss / supple_index.faiss) of the original MedRAGent with a
platform-managed knowledge base.

One chunk per MeSH descriptor:

    ### Term: Diabetes Mellitus, Type 1
    UI: D003922
    Tree Numbers: C18.452.394.500; C19.705.400.625
    Entry Terms: Diabetes Mellitus, Type I | IDDM | ...
    Scope Note: A chronic disorder characterized by ...

Usage
-----
    # 1) download the raw XML (about 300 MB compressed) - or fetch manually from
    #    https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/
    python mesh_to_kb.py --download

    # 2) full conversion (~31k descriptors)
    python mesh_to_kb.py --xml desc2026.xml --out mesh_full.txt

    # 3) recommended for the demo case: only trees relevant to a screening
    #    domain, keeps the Dify Cloud knowledge base small and retrieval sharp
    #    Suggested top-level branches: C=Diseases, E=Techniques/Equipment,
    #    F=Psychiatry/Psychology, G=Biological Sciences
    python mesh_to_kb.py --xml desc2026.xml --out mesh_demo.txt \
        --trees C E F G --max-records 30000

In Dify, import with the custom segment separator ``###`` (see dify/SETUP.md).
"""

import argparse
import gzip
import os
import shutil
import urllib.request
import xml.etree.ElementTree as ET

DESC_URL = "https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/desc2026.gz"
DESC_LOCAL_XML = "desc2026.xml"


def download(url: str = DESC_URL, dest_dir: str = ".") -> str:
    """Download and gunzip the MeSH descriptors archive -> desc2026.xml."""
    gz_path = os.path.join(dest_dir, "desc2026.gz")
    xml_path = os.path.join(dest_dir, DESC_LOCAL_XML)

    if os.path.exists(xml_path):
        print(f"[skip] {xml_path} already exists")
        return xml_path

    print(f"Downloading {url} ...")
    urllib.request.urlretrieve(url, gz_path)
    print(f"Extracting {gz_path} ...")
    with gzip.open(gz_path, "rb") as src, open(xml_path, "wb") as dst:
        shutil.copyfileobj(src, dst)
    os.remove(gz_path)
    return xml_path


def iter_descriptors(xml_path: str):
    """Stream DescriptorRecord elements without loading the whole tree."""
    context = ET.iterparse(xml_path, events=("end",))
    for event, elem in context:
        if elem.tag == "DescriptorRecord":
            yield elem
            elem.clear()


def parse_descriptor(elem: ET.Element) -> dict:
    """Extract the fields that matter for retrieval-augmented query expansion."""
    def text(path: str) -> str:
        node = elem.find(path)
        return node.text.strip() if node is not None and node.text else ""

    ui = text("DescriptorUI")
    name = text("DescriptorName/String")

    # In the MeSH XSU schema the scope note lives inside the preferred Concept
    scope = ""
    for concept in elem.findall("ConceptList/Concept"):
        if concept.get("PreferredRecord", "Y") == "Y":
            note = concept.findtext("ScopeNote")
            if note:
                scope = note.strip()
            break

    tree_numbers = [n.text.strip() for n in elem.findall("TreeNumberList/TreeNumber") if n.text]
    entry_terms = []
    for concept in elem.findall("ConceptList/Concept"):
        preferred = concept.get("PreferredRecord", "Y") == "Y"
        for term in concept.findall("TermList/Term"):
            if term.get("ConceptPreferredTerm", "Y") == "Y" or preferred:
                label = (term.findtext("String") or "").strip()
                if label and label != name:
                    entry_terms.append(label)
    # de-duplicate, keep order
    entry_terms = list(dict.fromkeys(entry_terms))

    return {
        "ui": ui,
        "name": name,
        "scope": scope,
        "tree_numbers": tree_numbers,
        "entry_terms": entry_terms,
    }


def matches_trees(tree_numbers, trees) -> bool:
    """A descriptor matches if any of its tree numbers starts with any prefix."""
    return any(tn.startswith(prefix) for tn in tree_numbers for prefix in trees)


def format_chunk(rec: dict) -> str:
    lines = [
        f"### Term: {rec['name']}",
        f"UI: {rec['ui']}",
    ]
    if rec["tree_numbers"]:
        lines.append("Tree Numbers: " + "; ".join(rec["tree_numbers"]))
    if rec["entry_terms"]:
        lines.append("Entry Terms: " + " | ".join(rec["entry_terms"]))
    if rec["scope"]:
        lines.append(f"Scope Note: {rec['scope']}")
    return "\n".join(lines)


def convert(xml_path: str, out_path: str, trees=None, max_records: int = 0) -> int:
    chunks = []
    total = 0
    for elem in iter_descriptors(xml_path):
        total += 1
        rec = parse_descriptor(elem)
        if trees and not matches_trees(rec["tree_numbers"], trees):
            continue
        chunks.append(format_chunk(rec))
        if max_records and len(chunks) >= max_records:
            break

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(chunks))

    print(f"Scanned {total} descriptors, wrote {len(chunks)} chunks -> {out_path}")
    size_mb = os.path.getsize(out_path) / 1e6
    print(f"File size: {size_mb:.1f} MB")
    return len(chunks)


def main():
    parser = argparse.ArgumentParser(description="MeSH XML -> Dify knowledge base corpus")
    parser.add_argument("--download", action="store_true", help="download the descriptors archive first")
    parser.add_argument("--xml", default="desc2026.xml", help="path to the descriptors XML")
    parser.add_argument("--out", default="mesh_kb.txt", help="output text corpus")
    parser.add_argument("--trees", nargs="*", default=None,
                        help="keep only descriptors under these tree number prefixes, e.g. C19 C23")
    parser.add_argument("--max-records", type=int, default=0, help="stop after N descriptors (0 = all)")
    args = parser.parse_args()

    if args.download:
        args.xml = download(dest_dir=os.path.dirname(os.path.abspath(args.out)) or ".")

    if not os.path.exists(args.xml):
        parser.error(f"MeSH XML not found at {args.xml}. Run with --download or fetch it manually.")

    n = convert(args.xml, args.out, trees=args.trees, max_records=args.max_records)
    if n == 0:
        raise SystemExit("No descriptors matched --trees filter; check the prefixes.")


if __name__ == "__main__":
    main()
