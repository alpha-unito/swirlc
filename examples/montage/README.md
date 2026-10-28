# Montage: small dataset test on Fedarcs

`config_get_dataset_small.json` keeps the original centre (`56.7 24.0`) and uses:

- `degrees: 0.05`, instead of 2.0.
- Three 2MASS bands: J/blue, H/green, K/red, instead of DSS.
- `n_iter: 100`, instead of 100000. This affects later background modelling,
  not the amount downloaded.

The dataset workflow produced 15 FITS images (five per band), eight overlap
pairs per band, and about 20 MiB total on 2026-10-27. Three bands preserve the
current RGB workflow's required red/green/blue outputs. The region generator
still adds a fixed 3000-pixel border; smaller degrees alone does not shrink
all later processing proportionally.

Run on the coordinator with the existing project-local Montage installation
and the venv containing cwltool and Astropy:

```bash
cd /mnt/shared/tfogliobonda/swirlc
. venv/bin/activate
export PATH="$PWD/.tools/montage/usr/bin:$PATH"
export LD_LIBRARY_PATH="$PWD/.tools/montage/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
mkdir -p build/montage/tmp
python -m cwltool --no-container --preserve-environment LD_LIBRARY_PATH \
  --outdir examples/montage/data-small \
  --tmpdir-prefix "$PWD/build/montage/tmp/cwl-" \
  examples/montage/main_get_dataset.cwl examples/montage/config_get_dataset_small.json
```

The local tool installation contains Ubuntu's `montage`, `montage-gridtools`,
and `libwcstools1t64` packages, extracted under `.tools/montage` without sudo.
The runner must preserve `LD_LIBRARY_PATH` for those libraries. JavaScript
expressions use cwltool's existing Docker fallback (`node:alpine`).

Input for the later mosaic workflow:
`examples/montage/data-small/config_montage.json`.
Dataset-run log: `build/montage/get-dataset-small.log`.
The dataset files are validated; `main_montage.cwl` has not been run.

## Local dataset run

On 2026-10-27, the unchanged workflow and small configuration completed locally
with cwltool. This run produced 12 FITS images (four per band), six overlap
pairs per band, and 15.6 MiB of output. The archive result can change over time;
the earlier Fedarcs run above returned five images per band. All FITS files and
configuration references were validated.

The locally built Montage 7.0 commands are under `.tools/montage/Montage-main/bin`.
With `uv`, cwltool, Astropy, and Node.js available, reproduce the run with:

```bash
export PATH="$PWD/.tools/montage/Montage-main/bin:$PATH"
mkdir -p build/montage/tmp examples/montage/data-small
uv run --no-project --with cwltool --with astropy python -m cwltool \
  --no-container --skip-schemas --parallel --parallel-max 3 \
  --outdir examples/montage/data-small \
  --tmpdir-prefix "$PWD/build/montage/tmp/cwl-" \
  --cachedir "$PWD/build/montage/cwl-cache" \
  examples/montage/main_get_dataset.cwl examples/montage/config_get_dataset_small.json \
  > build/montage/get-dataset-small.result.json 2> build/montage/get-dataset-small.log
```

The generated input for the mosaic workflow is `data-small/config_montage.json`;
`build/montage/dataset-summary.json` records the local validation results.

## Distributed Fedarcs run

`streamflow-fedarcs.yml` places band-level work on `fd-00`/`fd-01` and scatters
projection, pairwise fitting, and background correction over `fd-02`–`fd-04`.
Translate, compile, and launch from the coordinator. The configuration uses
`tfogliobonda`'s shared paths and ports 25900 and 25910–25914.

Each deployment declares its persistent tool environment in
`streamflow-fedarcs.yml` (the workers reuse the coordinator's mapping):

```yaml
environment:
  PATH: /mnt/shared/tfogliobonda/swirlc/venv/bin:/mnt/shared/tfogliobonda/swirlc/.tools/montage/usr/bin:/usr/local/bin:/usr/bin:/bin
  LD_LIBRARY_PATH: /mnt/shared/tfogliobonda/swirlc/.tools/montage/usr/lib/x86_64-linux-gnu
  SWIRLC_PYTHON: /mnt/shared/tfogliobonda/swirlc/venv/bin/python
```

The compiler writes these exports into every generated launcher, for runtime
preparation and execution. Recompilation preserves them from configuration;
generated files need no edits. Values are literal strings: `$PATH`, `${...}`,
and shell commands are not expanded. Use complete paths. Activating the
coordinator's venv alone does not configure SSH workers.

The shared library directory includes `libwcstools.so.1` and `libcfitsio.so.10`;
CFITSIO was absent from the worker nodes and was copied from the coordinator.
The small distributed run completed successfully. Its artifacts on Fedarcs are
under `build/montage-env-distributed`: `execution.log`, `validation.json`, and
`results/`. All six FITS arrays match the coordinator-only run exactly; the four
PNGs decode successfully at 180×180 pixels. This run used freshly compiled,
unmodified launchers, with their hashes checked on all worker deployments.
