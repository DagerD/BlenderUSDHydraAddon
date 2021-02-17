#**********************************************************************
# Copyright 2020 Advanced Micro Devices, Inc
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#********************************************************************
import math

from ..node_parser import NodeParser


class ShaderNodeBsdfPrincipled(NodeParser):
    def export(self):
        def enabled(val):
            if val is None:
                return False

            if isinstance(val.data, float) and math.isclose(val.data, 0.0):
                return False

            if isinstance(val.data, tuple) and \
               math.isclose(val.data[0], 0.0) and \
               math.isclose(val.data[1], 0.0) and \
               math.isclose(val.data[2], 0.0):
                return False

            return True

        # GETTING REQUIRED INPUTS
        # Note: if some inputs are not needed they won't be taken

        base_color = self.get_input_value('Base Color')

        subsurface = self.get_input_value('Subsurface')
        subsurface_radius = None
        subsurface_color = None
        if enabled(subsurface):
            subsurface_radius = self.get_input_value('Subsurface Radius')
            subsurface_color = self.get_input_value('Subsurface Color')

        metallic = self.get_input_value('Metallic')
        specular = self.get_input_value('Specular')
        specular_tint = self.get_input_value('Specular Tint')
        roughness = self.get_input_value('Roughness')

        anisotropic = None
        anisotropic_rotation = None
        if enabled(metallic):
            # TODO: use Specular Tint input
            anisotropic = self.get_input_value('Anisotropic')
            if enabled(anisotropic):
                anisotropic_rotation = self.get_input_value('Anisotropic Rotation')
                # anisotropic_rotation = 0.5 - (anisotropic_rotation % 1.0)

        sheen = self.get_input_value('Sheen')
        sheen_tint = None
        if enabled(sheen):
            sheen_tint = self.get_input_value('Sheen Tint')

        clearcoat = self.get_input_value('Clearcoat')
        clearcoat_roughness = None
        if enabled(clearcoat):
            clearcoat_roughness = self.get_input_value('Clearcoat Roughness')

        ior = self.get_input_value('IOR')

        transmission = self.get_input_value('Transmission')
        transmission_roughness = None
        if enabled(transmission):
            transmission_roughness = self.get_input_value('Transmission Roughness')

        emission = self.get_input_value('Emission')
        emission_strength = self.get_input_value('Emission Strength')

        alpha = self.get_input_value('Alpha')
        # transparency = 1.0 - alpha

        normal = self.get_input_link('Normal')
        clearcoat_normal = self.get_input_link('Clearcoat Normal')
        tangent = self.get_input_link('Tangent')

        # CREATING STANDARD SURFACE
        standard_surface = self.create_node('standard_surface', 'surfaceshader', {
            'base': 1.0,
            'base_color': base_color,
            'diffuse_roughness': roughness,
            'normal': normal,
            'tangent': tangent,
        })

        if enabled(metallic):
            standard_surface.set_input('metalness', metallic)

        if enabled(specular):
            standard_surface.set_inputs({
                'specular': specular,
                'specular_color': base_color,
                'specular_roughness': roughness,
                'specular_IOR': ior,
                'specular_anisotropy': anisotropic,
                'specular_rotation': anisotropic_rotation,
            })

        if enabled(transmission):
            standard_surface.set_inputs({
                'transmission': transmission,
                'transmission_color': base_color,
                'transmission_extra_roughness': transmission_roughness,
            })

        if enabled(subsurface):
            standard_surface.set_inputs({
                'subsurface': subsurface,
                'subsurface_color': subsurface_color,
                'subsurface_radius': subsurface_radius,
                'subsurface_anisotropy': anisotropic,
            })

        if enabled(sheen):
            standard_surface.set_inputs({
                'sheen': sheen,
                'sheen_color': base_color,
                'sheen_roughness': roughness,
            })

        if enabled(clearcoat):
            standard_surface.set_inputs({
                'coat': clearcoat,
                'coat_color': base_color,
                'coat_roughness': clearcoat_roughness,
                'coat_IOR': ior,
                'coat_anisotropy': anisotropic,
                'coat_rotation': anisotropic_rotation,
                'coat_normal': clearcoat_normal,
            })

        if enabled(emission):
            standard_surface.set_inputs({
                'emission': emission_strength,
                'emission_color': emission,
            })

        return standard_surface


class ShaderNodeBsdfDiffuse(NodeParser):
    def export(self):
        color = self.get_input_value('Color')
        roughness = self.get_input_value('Roughness')
        normal = self.get_input_link('Normal')

        diffuse = self.create_node('diffuse_brdf', 'BSDF', {
            'color': color,
            'roughness': roughness,
            'normal': normal,
        })

        return diffuse
