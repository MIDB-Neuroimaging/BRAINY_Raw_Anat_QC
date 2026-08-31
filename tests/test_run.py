import os
import tempfile
import unittest
from unittest.mock import patch

import run


class RunHelpersTest(unittest.TestCase):
    def test_output_paths_support_uncompressed_nifti(self):
        masked, registered = run.output_paths(
            '/data/sub-01/ses-01/anat/sub-01_ses-01_run-1_T1w.nii',
            '/outputs',
            'T1w',
        )
        self.assertEqual(
            masked,
            '/outputs/sub-01/ses-01/anat/sub-01_ses-01_run-1_desc-brain_mask.nii.gz',
        )
        self.assertEqual(
            registered,
            '/outputs/sub-01/ses-01/anat/sub-01_ses-01_run-1_space-MNI152NLin2009cAsym_T1w.nii.gz',
        )

    def test_output_paths_use_qalas_suffix(self):
        _, registered = run.output_paths(
            '/data/sub-01/anat/sub-01_inv-2_QALAS.nii.gz',
            '/outputs',
            'T1w',
        )
        self.assertTrue(registered.endswith('sub-01_inv-2_space-MNI152NLin2009cAsym_QALAS.nii.gz'))

    def test_default_filter_contains_current_image_selection(self):
        filters = run.load_filter_file('filters/default.json')
        self.assertEqual(filters['T1w']['suffix'], 'T1w')
        self.assertEqual(filters['T2w']['suffix'], 'T2w')
        self.assertEqual(filters['QALAS']['inv'], '2')

    def test_subject_relative_path_does_not_depend_on_session_depth(self):
        self.assertEqual(
            run.subject_relative_path('/data/sub-01/anat/sub-01_T2w.nii.gz'),
            os.path.join('sub-01', 'anat', 'sub-01_T2w.nii.gz'),
        )
        self.assertEqual(
            run.subject_relative_path('/data/sub-01/ses-01/anat/sub-01_T2w.nii.gz'),
            os.path.join('sub-01', 'ses-01', 'anat', 'sub-01_T2w.nii.gz'),
        )

    def test_synthstrip_uses_argument_list_and_checks_failure(self):
        with patch('run.subprocess.run') as run_process:
            run.run_synthstrip('/data/input file.nii', '/outputs/mask.nii.gz')
        run_process.assert_called_once_with(
            ['python3', '/freesurfer/mri_synthstrip', '-i', '/data/input file.nii',
             '-o', '/outputs/mask.nii.gz'],
            check=True,
        )

    def test_copy_sidecar_is_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = os.path.join(directory, 'input.nii')
            output_path = os.path.join(directory, 'output.nii.gz')
            with open(input_path, 'wb'):
                pass
            run.copy_sidecar(input_path, output_path)
            self.assertFalse(os.path.exists(os.path.join(directory, 'output.json')))


if __name__ == '__main__':
    unittest.main()
