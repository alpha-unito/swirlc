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
