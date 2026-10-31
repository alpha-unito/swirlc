#!/usr/bin/env bash
# Download only the selected chromosome inputs; keep completed downloads.
set -euo pipefail
EXAMPLE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
case "${1:-all}" in
  1) chromosomes=(1) ;;
  all) chromosomes=({1..10}) ;;
  *) echo "Usage: $0 [1|all]" >&2; exit 2 ;;
esac

fetch() {
  local url=$1 target=$2
  [[ -s "$target" ]] && return 0
  mkdir -p "$(dirname -- "$target")"
  echo "Downloading $target"
  curl --fail --location --retry 3 --output "$target.part" "$url"
  if [[ "$target" == *.gz ]]; then
    gzip -t "$target.part"
  fi
  mv -- "$target.part" "$target"
}

base=https://raw.githubusercontent.com/pegasus-isi/1000genome-workflow/master/data
fetch "$base/20130502/columns.txt" "$EXAMPLE/data/20130502/columns.txt"
for chromosome in "${chromosomes[@]}"; do
  fetch "$base/20130502/ALL.chr${chromosome}.250000.vcf.gz" \
    "$EXAMPLE/data/20130502/ALL.chr${chromosome}.250000.vcf.gz"
  name="ALL.chr${chromosome}.phase3_shapeit2_mvncall_integrated_v5.20130502.sites.annotation.vcf.gz"
  fetch "https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/supporting/functional_annotation/filtered/$name" \
    "$EXAMPLE/data/20130502/sifting/$name"
done
for population in AFR ALL AMR EAS EUR GBR SAS; do
  fetch "$base/populations/$population" "$EXAMPLE/data/populations/$population"
done
