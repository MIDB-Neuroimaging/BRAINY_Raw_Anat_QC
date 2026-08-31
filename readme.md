This repo contains the Dockerfile for building a simple utility to help visualize T1w, T2w, and QALAS
MRI data. The pipeline assumes BIDS formatting of an input dataset and follows the argument
structure of a BIDS application. With that in mind it can be run as follows:

>> brainy_qc /bids_dir /output_dir participant

Processing can also be restricted to a specific subject or session by adding --participant_label or
--session_id flags.

The pipeline looks for T1w/T2w/QALAS scans and tries to make snapshot png images for each of them. Once
an image is found, it is skull stripped by SynthStrip, then it is aligned to MNI152NLin2009cAsym space using a
12 DOF transformation in DIPY. Then a png is generated that displays three axial, coronal, and sagittal
views of the original MRI image that has been linearly transformed to MNI152NLin2009cAsym space. The color intensities
in the plot default to having a lower/upper bound on intensity of 1st/99th percentile of signal intensity found within the brain mask.

If QALAS data is available in the BIDS dataset, png snapshots will only be created if there is one QALAS volume
with naming following the pattern ".../anat/...inv-2_QALAS.ni...". If a file satisfiying this naming is present,
the image will be registered to the T1w MNI152NLin2009cAsym template under the image_templates folder, same as would
occur if the utility instead found a T1w image. T2w images are instead registered to the T2w MNI152NLin2009cAsym template.

## Container usage

The published image is available from GitHub Container Registry:

	ghcr.io/midb-neuroimaging/brainy_raw_anat_qc_container

Pull the latest image with:

	docker pull ghcr.io/midb-neuroimaging/brainy_raw_anat_qc_container:latest

Run it by mounting the BIDS input and output directories:

	docker run --rm \
	  -v /path/to/bids_dir:/bids_dir:ro \
	  -v /path/to/output_dir:/output_dir \
	ghcr.io/midb-neuroimaging/brainy_raw_anat_qc_container:latest \
	  /bids_dir /output_dir participant

The package may require authentication if it is private. Create a GitHub personal access token with
`read:packages`, then log in without putting the token in shell history:

	export CR_PAT=your_token
	printf '%s' "$CR_PAT" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin

## Building locally

Build the image from the repository root with:

	docker build -t brainy_raw_anat_qc_container:local .

The adult MNI templates in `image_templates/` are copied into the image during the build, so both template
files must be present in the build context.

## Creating a tagged release

The GitHub Actions workflow builds and publishes automatically when a semantic-version tag is pushed. Stable
releases and prereleases use annotated tags beginning with `v`:

	git tag -a v1.0.0 -m "Release v1.0.0"
	git push origin v1.0.0

The initial beta release is `v0.1.0-beta.1`:

	git tag -a v0.1.0-beta.1 -m "Release v0.1.0-beta.1"
	git push origin v0.1.0-beta.1

The workflow publishes these tags:

- `1.0.0` for the exact release
- `1.0` and `1` for compatible release lines
- `latest` for builds from the default branch
- a commit-specific `sha-...` tag for traceability

To use a release, pull its immutable version tag instead of `latest`:

	docker pull ghcr.io/midb-neuroimaging/brainy_raw_anat_qc_container:1.0.0



Related links:

SynthStrip - https://surfer.nmr.mgh.harvard.edu/docs/synthstrip/ 

DIPY - https://dipy.org/ 

TemplateFlow - https://www.templateflow.org/browse/ 

nibabel - https://nipy.org/nibabel/ 
