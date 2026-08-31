#!/usr/bin/python3

import os, glob, shutil
import subprocess
import argparse

TEMPLATE_PATH = '/image_templates/tpl-MNI152NLin2009cAsym_res-01_mask-applied_{}.nii.gz'


def nifti_extension(file_path):
    """Return the supported NIfTI extension for a path."""
    if file_path.endswith('.nii.gz'):
        return '.nii.gz'
    if file_path.endswith('.nii'):
        return '.nii'
    raise ValueError('Expected a .nii or .nii.gz input: ' + file_path)


def subject_relative_path(input_file_path):
    """Return the input path beginning at its BIDS subject directory."""
    input_path = os.path.abspath(input_file_path)
    path_parts = input_path.split(os.sep)
    subject_index = next((index for index, part in enumerate(path_parts) if part.startswith('sub-')), None)
    if subject_index is None:
        raise ValueError('Input path must contain a BIDS subject directory: ' + input_file_path)
    return os.path.join(*path_parts[subject_index:])


def output_paths(input_file_path, output_destination, contrast):
    """Build output paths while always writing registered images as .nii.gz."""
    relative_path = subject_relative_path(input_file_path)
    input_name = os.path.basename(relative_path)
    extension = nifti_extension(input_name)
    input_stem = input_name[:-len(extension)]
    output_base = os.path.join(output_destination, os.path.dirname(relative_path))
    if input_stem.endswith('_QALAS'):
        output_suffix = 'QALAS'
    else:
        output_suffix = contrast
    masked_path = os.path.join(output_base, 'masked-brain_{}.nii.gz'.format(output_suffix))
    registered_path = os.path.join(
        output_base,
        'reg-MNI152NLin2009cAsym_{}.nii.gz'.format(output_suffix),
    )
    return masked_path, registered_path


def sidecar_path(nifti_path):
    """Return the JSON sidecar path for either supported NIfTI extension."""
    return nifti_path[:-len(nifti_extension(nifti_path))] + '.json'


def run_synthstrip(input_file_path, stripped_out_file):
    """Run SynthStrip and fail immediately if skull stripping fails."""
    subprocess.run(
        ['python3', '/freesurfer/mri_synthstrip', '-i', input_file_path, '-o', stripped_out_file],
        check=True,
    )


def copy_sidecar(input_file_path, output_file_path):
    """Copy an input JSON sidecar when one is available."""
    input_sidecar = sidecar_path(input_file_path)
    if os.path.exists(input_sidecar):
        shutil.copyfile(input_sidecar, sidecar_path(output_file_path))



def register_images(input_file_path, output_destination, reuse_existing_output_file = True):
    '''
    
    '''
    
    #Input file path = full path to either T1w or T2w image
    #Output Destination = the top directory for outputs (i.e. same for all subjects)
    
    import nibabel as nib
    import numpy as np
    import dipy
    from dipy import align

    partial_sub_path = subject_relative_path(input_file_path)
    if 'T1w' in partial_sub_path:
        contrast = 'T1w'
    elif 'T2w' in partial_sub_path:
        contrast = 'T2w'
    elif 'QALAS.nii' in partial_sub_path:
        contrast = 'T1w'
    else:
        raise ValueError('Unsupported anatomical contrast in input: ' + input_file_path)

    stripped_out_file, final_registered_out_file = output_paths(input_file_path, output_destination, contrast)
    os.makedirs(os.path.dirname(final_registered_out_file), exist_ok=True)

    if reuse_existing_output_file and os.path.exists(final_registered_out_file):
        print('Using already existing registered out file with name: {}'.format(final_registered_out_file))
        if not os.path.exists(stripped_out_file):
            run_synthstrip(input_file_path, stripped_out_file)
        return final_registered_out_file, stripped_out_file

    run_synthstrip(input_file_path, stripped_out_file)
    
    print('Attempting Native to MNI152NLin2009cAsym Registration using DIPY: ')
    template_image_path = TEMPLATE_PATH.format(contrast)
    template_image = dipy.io.image.load_nifti(template_image_path)
    registered_img = align.affine_registration(stripped_out_file, template_image[0], static_affine=template_image[1])

    temp_img_to_align = nib.load(input_file_path)
    affine = registered_img[1]
    new_affine = np.matmul(np.linalg.inv(affine), temp_img_to_align.affine)
    new_nifti = nib.nifti1.Nifti1Image(temp_img_to_align.get_fdata(), new_affine, header=temp_img_to_align.header)
    nib.save(new_nifti, final_registered_out_file)
        
    return final_registered_out_file, stripped_out_file

def make_slices_image(image_nifti_path, slice_info_dict, output_img_name, close_plot = True,
                     upsample_factor = 2, mask_path = None):
    '''Takes a nifti and plots slices of the nifti according to slices_info_dict
    
    Parameters
    ----------
    image_nifti_path : str
        Path to nifti image to make plot with
    slice_info_dict : dict
        Dictionary that formats how the picture
        will be formatted. See example below.
    output_img_name : str
        The name/full path of the image
        to be created by this function
    close_plot : bool, default True
        Whether to close the plot after it
        is rendered
    mask_path : str or None, default None
        A masked version of the brain (with signal intensities).
        This will can be used to help with image contrast.
        
    Example slice_info_dict. The first entry in each key's
    list dictates which plane is being imaged. The second
    entry indicates where (in RAS) the center of the plane
    should be placed. And the third and fourth entries dictate
    the range of voxels to be included in the slice. For example,
    125 would mean that 250 units are included. Larger values
    will make larger field of views. 
    
    slice_info_dict = {'coronal_1' : [0, -25, 125, 125],
                   'coronal_2' : [0, 0, 125, 125],
                   'coronal_3' : [0, 25, 125, 125],
                   'sagittal_1' : [1, -50, 125, 125],
                   'sagittal_2' : [1, 0, 125, 125],
                   'sagittal_3' : [1, 30, 125, 125],
                   'axial_1' : [2, -50, 125, 125],
                   'axial_2' : [2, 0, 125, 125],
                   'axial_3' : [2, 50, 125, 125]}
    
    '''
    
    import nibabel as nib
    import numpy as np
    import matplotlib.pyplot as plt
    from scipy.interpolate import RegularGridInterpolator

    #Load the nifti image
    nifti_image = nib.load(image_nifti_path)
    
    #Load nifti mask (assume voxels > 0.5 are good)
    if type(None) == type(mask_path):
        vmin = None
        vmax = None
    else:
        mask_data = nib.load(mask_path).get_fdata()
        mask_vals = mask_data[mask_data > 0.5]
        if mask_vals.size == 0:
            raise ValueError('Brain mask contains no voxels above the threshold: ' + mask_path)
        vmin = np.percentile(mask_vals, 1)
        vmax = np.percentile(mask_vals, 99)
        #hist_results = np.histogram(mask_vals, bins = 100)
        #modal_value = hist_results[1][np.argmax(hist_results[0])]
        #vmin = modal_value*.3
        #vmax = modal_value*1.7
    
    #Grab data + affine
    full_data = nifti_image.get_fdata()
    full_affine = nifti_image.affine
    
    #Setup interpolator in scipy so we can
    #resample the image in RAS units instead
    #of voxel units
    i = np.arange(0,full_data.shape[0])
    j = np.arange(0,full_data.shape[1])
    k = np.arange(0,full_data.shape[2])
    interp = RegularGridInterpolator((i, j, k), full_data, method = 'linear', bounds_error = False)
    
    inv_affine = np.linalg.inv(full_affine) #To get to RAS
    imgs = [] #List to store all of the individual slice pixel intensities
    
    #Make each of the slice images
    for temp_img in slice_info_dict.keys():
        temp_setup = slice_info_dict[temp_img]
        temp_slice = []
        
        #Upsample by a factor of 2
        for i in range(-1*temp_setup[2]*upsample_factor,temp_setup[2]*upsample_factor):
            for j in range(-1*temp_setup[3]*upsample_factor, temp_setup[3]*upsample_factor):
                i_hat = i/upsample_factor
                j_hat = j/upsample_factor
                if temp_setup[0] == 0:
                    temp_slice.append(np.matmul(inv_affine, np.array([temp_setup[1],i_hat,j_hat,1])))
                elif temp_setup[0] == 1:
                    temp_slice.append(np.matmul(inv_affine, np.array([i_hat,temp_setup[1],j_hat, 1])))
                elif temp_setup[0] == 2:
                    temp_slice.append(np.matmul(inv_affine, np.array([i_hat,j_hat,temp_setup[1],1])))
                else:
                    raise ValueError('Error: the second entry must be 0,1,2 to indicate slicing axis')
        vals = interp(np.array(temp_slice)[:,0:3])
        imgs.append(np.rot90(vals.reshape((temp_setup[2]*2*upsample_factor, temp_setup[3]*2*upsample_factor))))

    dim1 = imgs[0].shape[0]
    dim2 = imgs[0].shape[1]
    full_img_panel = np.zeros((dim1*3, dim2*3))
    for i, temp_img in enumerate(imgs):
        y = np.mod(i, 3)
        x = np.floor(i/3)
        full_img_panel[int(x*dim1):int((1+x)*dim1),int(y*dim2):int((1+y)*dim2)] = temp_img
    full_img_panel[np.where(np.isnan(full_img_panel))] = 0


    fig = plt.figure(dpi = 250)
    plt.imshow(full_img_panel, cmap = 'gist_gray', interpolation='nearest', vmin=vmin, vmax=vmax)
    plt.xticks([])
    plt.yticks([])
    plt.axis('off')
    plt.savefig(output_img_name, bbox_inches='tight', pad_inches = 0)
    if close_plot:
        plt.close()
    
    return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('bids_dir', help='The path to the BIDS directory for your study', type=str)
    parser.add_argument('output_dir', help='The path to the folder where outputs will be stored', type=str)
    parser.add_argument('analysis_level', help='Should always be participant', type=str)
    parser.add_argument('--participant_label', '--participant-label', help='Subject label(s), separated by spaces', type=str)
    parser.add_argument('--session_id', '--session-id', help='Optional session label', type=str)
    parser.add_argument('--matplotlib_contrast', '--matplotlib-contrast', help='Use matplotlib to determine image contrast', action='store_true')
    args = parser.parse_args()

    bids_dir = os.path.abspath(args.bids_dir)
    output_dir = os.path.abspath(args.output_dir)
    if args.analysis_level != 'participant':
        raise ValueError('Error: analysis level must be participant, but program received: ' + args.analysis_level)

    if args.session_id:
        session_label = args.session_id if args.session_id.startswith('ses-') else 'ses-' + args.session_id
    else:
        session_label = None

    if args.participant_label:
        participants = [label if label.startswith('sub-') else 'sub-' + label
                        for label in args.participant_label.split()]
    else:
        participants = [path for path in glob.glob(os.path.join(bids_dir, 'sub-*'))
                        if os.path.isdir(path)]

    slice_info_dict = {'coronal_1': [0, -25, 125, 125], 'coronal_2': [0, 0, 125, 125],
                       'coronal_3': [0, 25, 125, 125], 'sagittal_1': [1, -50, 125, 125],
                       'sagittal_2': [1, 0, 125, 125], 'sagittal_3': [1, 30, 125, 125],
                       'axial_1': [2, -50, 125, 125], 'axial_2': [2, 0, 125, 125],
                       'axial_3': [2, 50, 125, 125]}

    processed_count = 0
    for participant in participants:
        subject_path = participant if os.path.isabs(participant) else os.path.join(bids_dir, participant)
        if not os.path.isdir(subject_path):
            raise AttributeError('Error: no directory found at: ' + subject_path)

        if session_label is None:
            sessions = [path for path in glob.glob(os.path.join(subject_path, 'ses*'))
                        if os.path.isdir(path)] or [subject_path]
        else:
            requested_session = os.path.join(subject_path, session_label)
            if not os.path.isdir(requested_session):
                raise AttributeError('Error: session with name ' + session_label + ' does not exist at ' + subject_path)
            sessions = [requested_session]

        for session_path in sessions:
            anat_dir = os.path.join(session_path, 'anat')
            images = {
                'T1w': glob.glob(os.path.join(anat_dir, '*T1w.nii')) + glob.glob(os.path.join(anat_dir, '*T1w.nii.gz')),
                'T2w': glob.glob(os.path.join(anat_dir, '*T2w.nii')) + glob.glob(os.path.join(anat_dir, '*T2w.nii.gz')),
                'QALAS': glob.glob(os.path.join(anat_dir, '*inv-2_QALAS.nii')) + glob.glob(os.path.join(anat_dir, '*inv-2_QALAS.nii.gz')),
            }
            for contrast, image_paths in images.items():
                for input_file_path in image_paths:
                    registered_path, masked_path = register_images(input_file_path, output_dir)
                    slice_img_path = registered_path.replace('.nii.gz', '_image-slice.png')
                    mask_for_plot = None if args.matplotlib_contrast else masked_path
                    make_slices_image(registered_path, slice_info_dict, slice_img_path,
                                      close_plot=True, upsample_factor=2, mask_path=mask_for_plot)
                    if os.path.exists(masked_path):
                        os.remove(masked_path)
                    copy_sidecar(input_file_path, registered_path)
                    processed_count += 1
            print('Finished with: {}'.format(session_path))

    if processed_count == 0:
        raise ValueError('No supported T1w, T2w, or inv-2 QALAS images were found.')


if __name__ == '__main__':
    main()