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
import bpy

from pxr import Sdf, UsdShade, Tf
import MaterialX as mx

from .. import utils
from ..utils import logging
log = logging.Log('export.material')


def sdf_name(mat: bpy.types.Material, input_socket_key='Surface'):
    ret = Tf.MakeValidIdentifier(mat.name_full)
    if input_socket_key != 'Surface':
        ret += "/" + Tf.MakeValidIdentifier(mat.name_full)

    return ret


def sync(materials_prim, mat: bpy.types.Material, obj: bpy.types.Object):
    """
    If material exists: returns existing material unless force_update is used
    In other cases: returns None
    """

    log("sync", mat, obj)

    doc = mat.hdusd.export(obj)
    if not doc:
        log.warn("MX export failed", mat)
        return None

    mx_file = utils.get_temp_file(".mtlx", f'{mat.name}{mat.hdusd.mx_node_tree.name if mat.hdusd.mx_node_tree else ""}')
    mx.writeToXmlFile(doc, str(mx_file))
    surfacematerial = next(node for node in doc.getNodes()
                           if node.getCategory() == 'surfacematerial')

    stage = materials_prim.GetStage()

    override_prim = stage.OverridePrim(materials_prim.GetPath().AppendChild(sdf_name(mat)))
    override_prim.GetReferences().AddReference(f"./{mx_file.name}", "/MaterialX")

    usd_mat = UsdShade.Material.Define(stage, override_prim.GetPath().AppendChild('Materials').
                                       AppendChild(surfacematerial.getName()))

    return usd_mat


def sync_update(materials_prim, mat: bpy.types.Material, obj: bpy.types.Object):
    """ Recreates existing material """

    log("sync_update", mat)

    stage = materials_prim.GetStage()
    mat_path = materials_prim.GetPath().AppendChild(sdf_name(mat))
    usd_mat = stage.GetPrimAtPath(mat_path)
    if usd_mat.IsValid():
        stage.RemovePrim(mat_path)

    return sync(materials_prim, mat, obj)


def sync_update_all(root_prim, mat: bpy.types.Material):
    sdf_mat_name = sdf_name(mat)
    mat_prims = []
    for obj_prim in root_prim.GetAllChildren():
        mat_prim = obj_prim.GetChild(sdf_mat_name)
        if mat_prim:
            mat_prims.append(mat_prim)

    if not mat_prims:
        return None

    doc = mat.hdusd.export(None)
    if not doc:
        # removing rpr_materialx_node in all material_prims
        return None

    mx_file = utils.get_temp_file(".mtlx", f'{mat.name}{mat.hdusd.mx_node_tree.name if mat.hdusd.mx_node_tree else ""}',
                                  is_rand=True)
    mx.writeToXmlFile(doc, str(mx_file))

    for mat_prim in mat_prims:
        mat_prim.GetReferences().ClearReferences()
        mat_prim.GetReferences().AddReference(f"./{mx_file.name}", "/MaterialX")
