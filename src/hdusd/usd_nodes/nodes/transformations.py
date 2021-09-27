# **********************************************************************
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
# ********************************************************************
import bpy
import math

from pxr import Usd, UsdGeom

from .base_node import USDNode


EDITABLE_TYPES = ('Xform',)


def enabled(val):
    if val is None:
        return False

    if isinstance(val, float) and math.isclose(val, 0.0):
        return False

    if isinstance(val, tuple) and \
            math.isclose(val[0], 0.0) and \
            math.isclose(val[1], 0.0) and \
            math.isclose(val[2], 0.0):
        return False

    return True


class TransformNode(USDNode):
    """Transforms input data"""
    bl_idname = 'usd.TransformNode'
    bl_label = "Transform"

    def update_data(self, context):
        self.reset()

    # region get/set
    def set_offset_x(self, value):
        self["offset_x"] = value

    def set_offset_y(self, value):
        self["offset_y"] = value

    def set_offset_z(self, value):
        self["offset_z"] = value

    def get_offset_x(self):
        return self.get("offset_x", 0.0)

    def get_offset_y(self):
        return self.get("offset_y", 0.0)

    def get_offset_z(self):
        return self.get("offset_z", 0.0)

    def set_scale_x(self, value):
        self["scale_x"] = value

    def set_scale_y(self, value):
        self["scale_y"] = value

    def set_scale_z(self, value):
        self["scale_z"] = value

    def get_scale_x(self):
        return self.get("scale_x", 1.0)

    def get_scale_y(self):
        return self.get("scale_y", 1.0)

    def get_scale_z(self):
        return self.get("scale_z", 1.0)

    def set_rotate_x(self, value):
        self["rotate_x"] = value

    def set_rotate_y(self, value):
        self["rotate_y"] = value

    def set_rotate_z(self, value):
        self["rotate_z"] = value

    def get_rotate_x(self):
        return self.get("rotate_x", 0.0)

    def get_rotate_y(self):
        return self.get("rotate_y", 0.0)

    def get_rotate_z(self):
        return self.get("rotate_z", 0.0)
    # endregion

    # region properties
    name: bpy.props.StringProperty(
        name="Name",
        description="Name for USD root primitive",
        default="Root",
        update=update_data
    )

    toggle_offset: bpy.props.BoolProperty(update=update_data)
    offset_x: bpy.props.FloatProperty(
        name="X offset", set=set_offset_x, get=get_offset_x, update=update_data)
    offset_y: bpy.props.FloatProperty(
        name="Y offset", set=set_offset_y, get=get_offset_y, update=update_data)
    offset_z: bpy.props.FloatProperty(
        name="Z offset", set=set_offset_z, get=get_offset_z, update=update_data)

    toggle_scale: bpy.props.BoolProperty(update=update_data)
    scale_x: bpy.props.FloatProperty(
        name="X axis", set=set_scale_x, get=get_scale_x, update=update_data)
    scale_y: bpy.props.FloatProperty(
        name="Y axis", set=set_scale_y, get=get_scale_y, update=update_data)
    scale_z: bpy.props.FloatProperty(
        name="Z axis", set=set_scale_z, get=get_scale_z, update=update_data)

    toggle_rotate: bpy.props.BoolProperty(update=update_data)
    rotate_x: bpy.props.FloatProperty(
        name="X origin", set=set_rotate_x, get=get_rotate_x, update=update_data)
    rotate_y: bpy.props.FloatProperty(
        name="Y origin", set=set_rotate_y, get=get_rotate_y, update=update_data)
    rotate_z: bpy.props.FloatProperty(
        name="Z origin", set=set_rotate_z, get=get_rotate_z, update=update_data)
    # endregion

    def draw_buttons(self, context, layout):
        layout.prop(self, 'name')

        row = layout.split(factor=0.4).row()
        row.alignment = 'LEFT'
        row.label(text='Offset')
        row.prop(self, 'toggle_offset', text='')

        row = layout.row()
        row.prop(self, 'offset_x')
        row.enabled = self.toggle_offset

        row = layout.row()
        row.prop(self, 'offset_y')
        row.enabled = self.toggle_offset

        row = layout.row()
        row.prop(self, 'offset_z')
        row.enabled = self.toggle_offset

        layout.separator()

        row = layout.split(factor=0.4).row()
        row.alignment = 'LEFT'
        row.label(text='Rotate')
        row.prop(self, 'toggle_rotate', text='')

        row = layout.row()
        row.prop(self, 'rotate_x')
        row.enabled = self.toggle_rotate

        row = layout.row()
        row.prop(self, 'rotate_y')
        row.enabled = self.toggle_rotate

        row = layout.row()
        row.prop(self, 'rotate_z')
        row.enabled = self.toggle_rotate

        layout.separator()

        row = layout.split(factor=0.4).row()
        row.alignment = 'LEFT'
        row.label(text='Scale')
        row.prop(self, 'toggle_scale', text='')

        row = layout.row()
        row.prop(self, 'scale_x')
        row.enabled = self.toggle_scale

        row = layout.row()
        row.prop(self, 'scale_y')
        row.enabled = self.toggle_scale

        row = layout.row()
        row.prop(self, 'scale_z')
        row.enabled = self.toggle_scale

    def compute(self, **kwargs):
        input_stage = self.get_input_link('Input', **kwargs)

        if input_stage is None:
            return

        if not self.name:
            return input_stage

        stage = self.cached_stage.create()
        UsdGeom.SetStageMetersPerUnit(stage, 1)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)

        prims = [prim for prim in input_stage.GetPseudoRoot().GetAllChildren()
                 if prim.GetTypeName() in EDITABLE_TYPES]

        for prim in prims:
            root_prim = UsdGeom.Xform.Define(stage, prim.GetPath())
            override_prim = stage.OverridePrim(root_prim.GetPath())
            override_prim.GetReferences().AddReference(input_stage.GetRootLayer().realPath,
                                                       prim.GetPath())

            if prim.GetName() != self.name:
                continue

            usd_geom = UsdGeom.Xform.Get(stage, override_prim.GetPath())
            value = (self.offset_x, self.offset_y, self.offset_z)

            if self.toggle_offset and enabled(value):
                if not override_prim.HasAttribute('xformOp:translate'):
                    usd_geom.AddTranslateOp()

                override_prim.GetAttribute('xformOp:translate').Set(value)

            value = (self.rotate_x, self.rotate_y, self.rotate_z)

            if self.toggle_rotate and enabled(value):
                if not override_prim.HasAttribute('xformOp:rotateXYZ'):
                    usd_geom.AddRotateXYZOp()

                override_prim.GetAttribute('xformOp:rotateXYZ').Set(value)

            value = (self.scale_x, self.scale_y, self.scale_z)

            if self.toggle_scale and enabled(value):
                if not override_prim.HasAttribute('xformOp:scale'):
                    usd_geom.AddScaleOp()

                override_prim.GetAttribute('xformOp:scale').Set(value)

        return stage
