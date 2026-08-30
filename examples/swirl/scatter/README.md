# SWIRL Scatter-Gather Workflow Example (Shell Commands)

This example showcases the SWIRL extended operational semantics with a pure shell-command pipeline:

$$\text{Step 1 (unzip archive.zip)} \longrightarrow \text{Step 2 (scattered: wc -c file size)} \longrightarrow \text{Step 3 (gather: cat summary)}$$

---

## 1. Pipeline Overview

1. **Step 1 (`unzip`) at location `l0`**:
   - Takes workflow input `archive.zip` from port `p_zip`.
   - Executes standard shell command `unzip -o archive.zip -d extracted`.
   - Produces a stream of extracted file items (`file_ID`) tagged with `ID` on port `p_file`.
   - Dispatches files dynamically to worker locations $y \in \{l_1, l_2, l_3\}$, followed by `eof`.

2. **Step 2 (`wc -c`) at worker locations `l1`, `l2`, `l3` (Scattered & Replicated `!` with choice `+`)**:
   - Replicated workers concurrently receive `(ID, file_ID)`.
   - Executes standard shell command `wc -c <extracted_file>` to compute the file size in bytes.
   - Forwards resulting size output (`size_ID`) on port `p_size` to gather location `lG`.
   - Propagates `eof` to `lG` upon stream completion.

3. **Step 3 (`cat`) at gather location `lG`**:
   - Concurrently collects size results from all worker locations until `eof` arrives from each.
   - Executes standard shell command `cat` on the gathered collection to produce final output `sizes_summary.txt`.

