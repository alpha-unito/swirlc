# Nested Scatter Example: Zip Extraction and File Inspection

This example demonstrates hierarchical (nested) scatter-gather workflow execution across distributed locations:

1. **Outer Scatter**: A list of $N$ `.zip` files is scattered across `zip_worker1` and `zip_worker2`.
2. **Local Extraction**: On each worker location, the archive is unpacked to obtain its $M$ constituent files.
3. **Inner (Nested) Scatter**: The extracted files are scattered across `file_worker1`, `file_worker2`, and `file_worker3`, where each file's size and preview are extracted.
4. **Inner Gather**: All $M$ inspection reports for a zip archive are gathered back onto the zip worker to produce a per-archive summary.
5. **Outer Gather**: All $N$ archive summaries are transferred back to the `coordinator`.
6. **Final Summary Step**: An aggregator step reduces the archive summaries into a single final global workflow report.

Each deployment maps to one SWIRL location. Each scatter binding lists every
deployment that should receive its worker trace.

## File Structure

```
scatter-nested-zip/
├── main.cwl               # Master workflow: outer scatter + final aggregation
├── process_zip.cwl        # Subworkflow: unzip + inner scatter + local gather
├── streamflow.yml         # Multi-location topology and step bindings
├── inputs.yml             # Input parameters (list of zip files)
├── clt/
│   ├── unzip.cwl          # CommandLineTool to unpack an archive
│   ├── inspect_file.cwl   # CommandLineTool to inspect file size and preview
│   ├── summarize_zip.cwl  # CommandLineTool to merge file inspection reports for one zip
│   └── final_summary.cwl  # CommandLineTool to produce the global report
├── scripts/
│   ├── unzip_archive.py
│   ├── inspect_file.py
│   ├── summarize_zip.py
│   └── final_summary.py
└── data/
    ├── archive_1.zip
    └── archive_2.zip
```
