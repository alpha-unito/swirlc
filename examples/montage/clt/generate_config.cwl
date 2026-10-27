cwlVersion: v1.2
class: CommandLineTool

$namespaces:
  s: https://schema.org/

$schemas:
 - https://schema.org/version/latest/schemaorg-current-http.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0009-0009-2600-613X
    s:email: mailto:alberto.mulone@unito.it
    s:name: Alberto Mulone
  - class: s:Person
    s:identifier: https://orcid.org/0000-0001-9290-2017
    s:email: mailto:iacopo.colonnelli@unito.it
    s:name: Iacopo Colonnelli

s:codeRepository: https://github.com/alpha-unito/cwl-montage-workflow
s:dateCreated: "2025-12-01"
s:license: https://spdx.org/licenses/Apache-2.0

hints:
  - class: DockerRequirement
    dockerPull: docker.io/python:3-slim
inputs:
  bands: 
    type:
      type: array
      items:
        type: record
        fields:
          bid: int
          survey: string
          band: string
          color: string
  diff_tbl: File[]
  corrected_tbl: File[]
  images_tbl: File[]
  image_fits: 
    type: 
      type: array 
      items:
        type: array
        items: File 
  n_iter: int
  projected_tbl: File[]
  statfile: File[]
  region: File
  region_oversized: File
outputs: 
  config_file:
    type: File
    outputBinding:
      glob: "config_montage.json"
    secondaryFiles:
      - $(inputs.diff_tbl.flat())
      - $(inputs.corrected_tbl.flat())
      - $(inputs.image_fits.flat())
      - $(inputs.images_tbl.flat())
      - $(inputs.projected_tbl.flat())
      - $(inputs.statfile.flat())
      - $(inputs.region)
      - $(inputs.region_oversized)
baseCommand: ["python", "generate.py"]
requirements:
  InlineJavascriptRequirement: {}
  InitialWorkDirRequirement:
    listing:
      - entry: $(inputs.diff_tbl.flat())
      - entry: $(inputs.corrected_tbl.flat())
      - entry: $(inputs.image_fits.flat())
      - entry: $(inputs.images_tbl.flat())
      - entry: $(inputs.projected_tbl.flat())
      - entry: $(inputs.statfile.flat())
      - entry: $(inputs.region)
      - entry: $(inputs.region_oversized)
      - entryname: 'generate.py' 
        entry: |
          import json
          import os
          def get_path(cwl_file, prefix=None):
            if prefix and not cwl_file["basename"].startswith(prefix):
              raise Exception(
                f"The file name {cwl_file['basename']} must starts with the prefix '{bid}'"
              )
            if not os.path.exists(cwl_file["basename"]):
              raise FileNotFoundError(os.path.join(os.getcwd(), cwl_file["basename"]))
            return cwl_file["basename"]
          bands = $(inputs.bands)
          diff_files = $(inputs.diff_tbl)
          projected_files = $(inputs.projected_tbl)
          stat_files = $(inputs.statfile)
          nested_image_files = $(inputs.image_fits)
          images_tbl_files = $(inputs.images_tbl)
          corrected_tbl_files = $(inputs.corrected_tbl)
          config_file = "config_montage.json"
          config = {
            "n_iter": $(inputs.n_iter),
            "region": {"class": "File", "path": "$(inputs.region.basename)"},
            "region_oversized": {
              "class": "File",
              "path": "$(inputs.region_oversized.basename)",
            },
            "bands": [],
          }
          for band, corrected_tbl_file, diff_file, projected_file, stat_file, image_files, images_tbl_file in zip(
            bands, corrected_tbl_files, diff_files, projected_files, stat_files, nested_image_files, images_tbl_files
          ):
            config["bands"].append(
              {
                "bid": band["bid"],
                "color": band["color"],
                "diff_tbl": {
                  "class": "File",
                  "path": get_path(diff_file, str(band["bid"])),
                },
                "projected_tbl": {
                  "class": "File",
                  "path": get_path(projected_file, str(band["bid"])),
                },
                "statfile": {
                  "class": "File",
                  "path": get_path(stat_file, str(band["bid"])),
                },
                "images_fits": [
                  {"class": "File", "path": get_path(cwl_file)}
                  for cwl_file in image_files
                ],
                "images_tbl": {
                  "class": "File",
                  "path": get_path(images_tbl_file, str(band["bid"])),
                },
                "corrected_tbl": {
                  "class": "File",
                  "path": get_path(corrected_tbl_file, str(band["bid"])) 
                }
              }
            )
          with open(config_file, "w") as fp:
              json.dump(config, fp, indent=2)

          