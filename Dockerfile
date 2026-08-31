#The base image is FreeSurfer's synthstrip package
FROM freesurfer/synthstrip@sha256:0fac3ee2f9ba4b579fc59265753f3e1e33f7153b6e473757aa3f7f0c85697b5d

#Install relevant python packages
RUN python3 -m pip install nibabel==3.2.2
RUN python3 -m pip install dipy==1.6.0
RUN python3 -m pip install matplotlib==3.3.4

#Make code and data directory
RUN mkdir /brainy_code && mkdir /image_templates

#Copy over images
ADD image_templates/tpl-MNI152NLin2009cAsym_res-01_mask-applied_T1w.nii.gz /image_templates/tpl-MNI152NLin2009cAsym_res-01_mask-applied_T1w.nii.gz
ADD image_templates/tpl-MNI152NLin2009cAsym_res-01_mask-applied_T2w.nii.gz /image_templates/tpl-MNI152NLin2009cAsym_res-01_mask-applied_T2w.nii.gz

#Copy code, assign permissions
ADD run.py /brainy_code/run.py
RUN chmod 555 -R /brainy_code
ENV PATH="${PATH}:/brainy_code"
RUN pipeline_name=brainy_qc && cp /brainy_code/run.py /brainy_code/$pipeline_name

#Define entrypoint
ENTRYPOINT ["brainy_qc"]
