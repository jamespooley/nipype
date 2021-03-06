# -*- coding: utf-8 -*-
"""Change directory to provide relative paths for doctests
   >>> import os
   >>> filepath = os.path.dirname( os.path.realpath( __file__ ) )
   >>> datadir = os.path.realpath(os.path.join(filepath, '../../testing/data'))
   >>> os.chdir(datadir)
"""
import nibabel as nb

from ..base import TraitedSpec, File, isdefined
from .base import DipyDiffusionInterface, DipyBaseInterfaceInputSpec

from ... import logging
IFLOGGER = logging.getLogger('interface')


class DKIInputSpec(DipyBaseInterfaceInputSpec):
    mask_file = File(exists=True, desc='An optional white matter mask')
    
class DKIOutputSpec(TraitedSpec):
    out_file = File(exists=True)
    fa_file = File(exists=True)
    md_file = File(exists=True)
    rd_file = File(exists=True)
    ad_file = File(exists=True)

    mk_file = File(exists=True)
    ak_file = File(exists=True)
    rk_file = File(exists=True)

class DKI(DipyDiffusionInterface):
    """
    Calculates the diffusion kurtosis model parameters

    Example
    -------
    >>> import nipype.interfaces.dipy as dipy
    >>> dki = dipy.DKI()
    >>> dki.inputs.in_file = 'diffusion.nii'
    >>> dki.inputs.in_bvec = 'bvecs'
    >>> dki.inputs.in_bval = 'bvals'
    >>> dki.run()  # doctest: SKIP+
    """

    def _run_interface(self, runtime):
        from dipy.reconst import dki
        from dipy.io.utils import nifti1_symmat
        gtab = self._get_gradient_table()

        img = nb.load(self.inputs.in_file)
        data = img.get_data()
        affine = img.affine
        mask = None
        if isdefined(self.inputs.mask_file):
            mask = nb.load(self.inputs.mask_file).get_data()

        # Fit the DKI model
        kurtosis_model = dki.DiffusionKurtosisModel(gtab)
        kurtosis_fit = kurtosis_model.fit(data, mask)
        lower_triangular = kurtosis_fit.lower_triangular()
        img = nifti1_symmat(lower_triangular, affine)
        out_file = self._gen_filename('dki')
        nb.save(img, out_file)
        IFLOGGER.info('DKI parameters image saved as {i}.format(i=out_file)')

        # FA, MD, RD, and AD
        for metric in ['fa', 'md', 'rd', 'ad', 'mk', 'ak', 'rk']:
            data = getattr(kurtosis_fit.metric).astype('float32')
            out_name = self._gen_filename(metric)
            nb.Nifti1Image(data, affine).to_filename(out_name)
            IFLOGGER.info('DKI {metric} image saved as {i}'.format(i=out_name,
                                                                   metric=metric))

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_file'] = self._gen_filename('dki')

        for metric in ['fa', 'md', 'rd', 'ad', 'mk', 'ak', 'rk']:
            outputs['{}'.format(metric)] = self._gen_filename(metric)

        return outputs


class DTIInputSpec(DipyBaseInterfaceInputSpec):
    mask_file = File(exists=True,
                     desc='An optional white matter mask')


class DTIOutputSpec(TraitedSpec):
    out_file = File(exists=True)
    fa_file = File(exists=True)
    md_file = File(exists=True)
    rd_file = File(exists=True)
    ad_file = File(exists=True)


class DTI(DipyDiffusionInterface):
    """
    Calculates the diffusion tensor model parameters

    Example
    -------

    >>> import nipype.interfaces.dipy as dipy
    >>> dti = dipy.DTI()
    >>> dti.inputs.in_file = 'diffusion.nii'
    >>> dti.inputs.in_bvec = 'bvecs'
    >>> dti.inputs.in_bval = 'bvals'
    >>> dti.run()  # doctest: +SKIP
    """
    input_spec = DTIInputSpec
    output_spec = DTIOutputSpec

    def _run_interface(self, runtime):
        from dipy.reconst import dti
        from dipy.io.utils import nifti1_symmat
        gtab = self._get_gradient_table()

        img = nb.load(self.inputs.in_file)
        data = img.get_data()
        affine = img.affine
        mask = None
        if isdefined(self.inputs.mask_file):
            mask = nb.load(self.inputs.mask_file).get_data()

        # Fit it
        tenmodel = dti.TensorModel(gtab)
        ten_fit = tenmodel.fit(data, mask)
        lower_triangular = ten_fit.lower_triangular()
        img = nifti1_symmat(lower_triangular, affine)
        out_file = self._gen_filename('dti')
        nb.save(img, out_file)
        IFLOGGER.info('DTI parameters image saved as {i}'.format(i=out_file))

        #FA MD RD and AD
        for metric in ["fa", "md", "rd", "ad"]:
            data = getattr(ten_fit,metric).astype("float32")
            out_name = self._gen_filename(metric)
            nb.Nifti1Image(data, affine).to_filename(out_name)
            IFLOGGER.info('DTI {metric} image saved as {i}'.format(i=out_name, metric=metric))

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_file'] = self._gen_filename('dti')

        for metric in ["fa", "md", "rd", "ad"]:
            outputs["{}_file".format(metric)] = self._gen_filename(metric)

        return outputs


class TensorModeInputSpec(DipyBaseInterfaceInputSpec):
    mask_file = File(exists=True,
                     desc='An optional white matter mask')


class TensorModeOutputSpec(TraitedSpec):
    out_file = File(exists=True)


class TensorMode(DipyDiffusionInterface):

    """
    Creates a map of the mode of the diffusion tensors given a set of
    diffusion-weighted images, as well as their associated b-values and
    b-vectors. Fits the diffusion tensors and calculates tensor mode
    with Dipy.

    .. [1] Daniel B. Ennis and G. Kindlmann, "Orthogonal Tensor
        Invariants and the Analysis of Diffusion Tensor Magnetic Resonance
        Images", Magnetic Resonance in Medicine, vol. 55, no. 1, pp. 136-146,
        2006.

    Example
    -------

    >>> import nipype.interfaces.dipy as dipy
    >>> mode = dipy.TensorMode()
    >>> mode.inputs.in_file = 'diffusion.nii'
    >>> mode.inputs.in_bvec = 'bvecs'
    >>> mode.inputs.in_bval = 'bvals'
    >>> mode.run()                                   # doctest: +SKIP
    """
    input_spec = TensorModeInputSpec
    output_spec = TensorModeOutputSpec

    def _run_interface(self, runtime):
        from dipy.reconst import dti

        # Load the 4D image files
        img = nb.load(self.inputs.in_file)
        data = img.get_data()
        affine = img.get_affine()

        # Load the gradient strengths and directions
        gtab = self._get_gradient_table()

        # Mask the data so that tensors are not fit for
        # unnecessary voxels
        mask = data[..., 0] > 50

        # Fit the tensors to the data
        tenmodel = dti.TensorModel(gtab)
        tenfit = tenmodel.fit(data, mask)

        # Calculate the mode of each voxel's tensor
        mode_data = tenfit.mode

        # Write as a 3D Nifti image with the original affine
        img = nb.Nifti1Image(mode_data, affine)
        out_file = self._gen_filename('mode')
        nb.save(img, out_file)
        IFLOGGER.info('Tensor mode image saved as {i}'.format(i=out_file))
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_file'] = self._gen_filename('mode')
        return outputs
