# CWL + Streamflow Scatter-Gather Example

This example demonstrates a distributed scatter-gather pipeline implemented in standard **CWL v1.2** with **Streamflow** orchestration, mirroring the behavior of the SWIRL scatter pipeline (`examples/swirl/scatter`).

---

## 1. Architecture & Mapping to SWIRL

| SWIRL Concept (`examples/swirl/scatter`) | CWL + Streamflow Representation (`examples/cwl/scatter`) | Role |
| :--- | :--- | :--- |
| **Location `l0`** | Deployment `l0` (Controller) | Stages input datasets `files_a` and `files_b` |
| **Step `s_sc`** (`ScatterPairer`) | `scatter: [file_a, file_b]` with `scatterMethod: dotproduct` | Pairs items `(files_a[i], files_b[i])` |
| **Workers `l1, l2, l3`** | Deployment `workers` (multi-node / worker pool) | Executes `compute.cwl` in parallel for each paired item |
| **Step `s_op`** + **`s_work`** | `compute.cwl` (`scripts/compute.py`) | Processes each item pair and produces a result file |
| **Step `s_G`** (`ScatterGather`) | CWL automatic gather (`compute/result` -> `File[]`) | Gathers all worker results into an array of files |
| **Location `lG`** | Deployment `lG` (Gather node) | Hosts the gathered result array and final step |
| **Step `s_post`** (`AnalyzeReport`) | `analyze.cwl` (`scripts/analyze.py`) | Consumes `File[]` to generate `analysis_report.txt` |

---

## 2. Directory Structure

```text
examples/cwl/scatter/
├── main.cwl               # CWL workflow with ScatterFeatureRequirement
├── compute.cwl            # CommandLineTool for parallel item computation
├── analyze.cwl            # CommandLineTool for post-gather analysis
├── inputs.yml             # CWL job input bindings / Streamflow settings
├── streamflow.yml         # Streamflow deployment configuration (local)
├── streamflow-split.yml   # Streamflow multi-deployment configuration (distributed)
├── README.md              # This documentation
├── scripts/
│   ├── compute.py         # Worker calculation script
│   └── analyze.py         # Aggregate statistical report script
└── data/
    ├── a_0.txt .. a_4.txt # Component A inputs (1-5 bytes)
    └── b_0.txt .. b_4.txt # Component B inputs (1-8 bytes)
```

---

## 3. Workflow Details

### A. `main.cwl`
```yaml
cwlVersion: v1.2
class: Workflow

requirements:
  ScatterFeatureRequirement: {}

inputs:
  files_a: File[]
  files_b: File[]

outputs:
  report:
    type: File
    outputSource: analyze/report

steps:
  compute:
    run: compute.cwl
    scatter: [file_a, file_b]
    scatterMethod: dotproduct
    in:
      file_a: files_a
      file_b: files_b
    out: [result]

  analyze:
    run: analyze.cwl
    in:
      inputs: compute/result
    out: [report]
```

### B. `streamflow.yml`
Binds the workflow steps to distinct deployments corresponding to SWIRL locations:
```yaml
version: v1.0
workflows:
  master:
    type: cwl
    config:
      file: main.cwl
      settings: inputs.yml
    bindings:
      - step: /
        target:
          deployment: l0
      - step: /compute
        target:
          deployment: workers
      - step: /analyze
        target:
          deployment: lG
```
