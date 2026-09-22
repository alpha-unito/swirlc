#!/bin/bash

# Download the workflow input data from the Pegasus 1000Genomes Workflow GitHub repository.

SCRIPT_DIRECTORY="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

mkdir -p "${SCRIPT_DIRECTORY}/data/20130502/sifting"
mkdir -p "${SCRIPT_DIRECTORY}/data/populations"

wget -O "${SCRIPT_DIRECTORY}/data/20130502/columns.txt" \
  https://raw.githubusercontent.com/pegasus-isi/1000genome-workflow/master/data/20130502/columns.txt

for i in {1..10}
do
  wget -O "${SCRIPT_DIRECTORY}/data/20130502/ALL.chr${i}.250000.vcf.gz" \
    https://github.com/pegasus-isi/1000genome-workflow/raw/master/data/20130502/ALL.chr${i}.250000.vcf.gz
  wget -O "${SCRIPT_DIRECTORY}/data/20130502/sifting/ALL.chr${i}.phase3_shapeit2_mvncall_integrated_v5.20130502.sites.annotation.vcf.gz" \
    https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/supporting/functional_annotation/filtered/ALL.chr${i}.phase3_shapeit2_mvncall_integrated_v5.20130502.sites.annotation.vcf.gz
done

for pop in "AFR" "ALL" "AMR" "EAS" "EUR" "GBR" "SAS"; do
  wget -O "${SCRIPT_DIRECTORY}/data/populations/${pop}" \
    https://raw.githubusercontent.com/pegasus-isi/1000genome-workflow/master/data/populations/${pop}
done
