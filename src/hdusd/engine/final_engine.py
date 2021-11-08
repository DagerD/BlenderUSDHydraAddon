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
import time
import numpy as np

from pxr import Usd, UsdAppUtils, Glf, Tf, UsdGeom
from pxr import UsdImagingGL, UsdImagingLite

import bpy
import bgl

from .engine import Engine
from ..utils import gl, time_str
from ..utils import usd as usd_utils
from ..export import object, world

from ..utils import logging
log = logging.Log('final_engine')


class FinalEngine(Engine):
    """ Final render engine """

    TYPE = 'FINAL'

    def __init__(self, render_engine):
        super().__init__(render_engine)

        self.width = 0
        self.height = 0

        self.render_layer_name = None

        self.status_title = ""

    def notify_status(self, progress, info):
        """ Display export/render status """
        self.render_engine.update_progress(progress)
        self.render_engine.update_stats(self.status_title, info)
        log(f"Status [{progress:.2}]: {info}")

    def _render_gl(self, scene):
        CLEAR_DEPTH = 1.0

        # creating draw_target
        draw_target = Glf.DrawTarget(self.width, self.height)
        draw_target.Bind()
        draw_target.AddAttachment("color", bgl.GL_RGBA, bgl.GL_FLOAT, bgl.GL_RGBA)

        # creating renderer
        renderer = UsdImagingGL.Engine()
        self._sync_render_settings(renderer, scene)

        # setting camera
        self._set_scene_camera(renderer, scene)

        renderer.SetRenderViewport((0, 0, self.width, self.height))
        renderer.SetRendererAov('color')

        root = self.stage.GetPseudoRoot()
        params = UsdImagingGL.RenderParams()
        params.renderResolution = (self.width, self.height)
        params.frame = Usd.TimeCode.Default()

        if scene.hdusd.final.data_source:
            world_data = world.WorldData.init_from_stage(self.stage)
        else:
            world_data = world.WorldData.init_from_world(scene.world)

        params.clearColor = world_data.clear_color

        try:
            renderer.Render(root, params)

        except Exception as e:
            log.error(e)

        self.update_render_result({
            'Combined': gl.get_framebuffer_data(self.width, self.height)
        })

        draw_target.Unbind()

        # it's important to clear data explicitly
        draw_target = None
        renderer = None

    def _render(self, scene):
        # creating renderer
        renderer = UsdImagingLite.Engine()
        self._sync_render_settings(renderer, scene)

        renderer.SetRenderViewport((0, 0, self.width, self.height))
        renderer.SetRendererAov('color')

        # setting camera
        self._set_scene_camera(renderer, scene)

        params = UsdImagingLite.RenderParams()
        render_images = {
            'Combined': np.empty((self.width, self.height, 4), dtype=np.float32)
        }

        renderer.Render(self.stage.GetPseudoRoot(), params)

        time_begin = time.perf_counter()
        while True:
            if self.render_engine.test_break():
                break

            percent_done = renderer.GetRenderStats()['percentDone']
            self.notify_status(percent_done / 100, f"Render Time: {time_str(time.perf_counter() - time_begin)} | Done: {round(percent_done)}%")

            if renderer.IsConverged():
                break

            renderer.GetRendererAov('color', render_images['Combined'].ctypes.data)
            self.update_render_result(render_images)

        renderer.GetRendererAov('color', render_images['Combined'].ctypes.data)
        self.update_render_result(render_images)

        # its important to clear data explicitly
        renderer = None

    def _set_scene_camera(self, renderer, scene):
        if scene.hdusd.final.nodetree_camera != '' and scene.hdusd.final.data_source:
            usd_camera = UsdAppUtils.GetCameraAtPath(self.stage, scene.hdusd.final.nodetree_camera)
        else:
            usd_camera = UsdAppUtils.GetCameraAtPath(self.stage, Tf.MakeValidIdentifier(scene.camera.data.name))
       
        gf_camera = usd_camera.GetCamera()
        renderer.SetCameraState(gf_camera.frustum.ComputeViewMatrix(),
                                gf_camera.frustum.ComputeProjectionMatrix())

    def render(self, depsgraph):
        if not self.stage:
            return

        scene = depsgraph.scene
        log(f"Start render [{self.width}, {self.height}]. "
            f"Hydra delegate: {scene.hdusd.final.delegate}")
        if self.render_engine.bl_use_gpu_context:
            self._render_gl(scene)
        else:
            self._render(scene)

        self.notify_status(1.0, "Finish render")

    def sync(self, depsgraph):
        scene = depsgraph.scene
        settings = scene.hdusd.final
        view_layer = depsgraph.view_layer

        self.render_layer_name = view_layer.name
        self.status_title = f"{scene.name}: {self.render_layer_name}"
        self.notify_status(0.0, "Start syncing")

        # Preparations for syncing
        time_begin = time.perf_counter()

        border = ((0, 0), (1, 1)) if not scene.render.use_border else \
            ((scene.render.border_min_x, scene.render.border_min_y),
             (scene.render.border_max_x - scene.render.border_min_x,
              scene.render.border_max_y - scene.render.border_min_y))

        screen_width = int(scene.render.resolution_x * scene.render.resolution_percentage / 100)
        screen_height = int(scene.render.resolution_y * scene.render.resolution_percentage / 100)

        self.width = int(screen_width * border[1][0])
        self.height = int(screen_height * border[1][1])

        self._sync(depsgraph)

        usd_utils.set_variant_delegate(self.stage, settings.is_gl_delegate)

        if self.render_engine.test_break():
            log.warn("Syncing stopped by user termination")
            return

        # setting enabling/disabling gpu context in render() method
        self.render_engine.bl_use_gpu_context = settings.is_gl_delegate

        log.info("Scene synchronization time:", time_str(time.perf_counter() - time_begin))
        self.notify_status(0.0, "Start render")

    def _sync(self, depsgraph):
        pass

    def update_render_result(self, render_images):
        result = self.render_engine.begin_result(0, 0, self.width, self.height,
                                                 layer=self.render_layer_name)
        render_passes = result.layers[0].passes

        images = []
        for p in render_passes:
            image = render_images.get(p.name)
            if image is None:
                image = np.zeros((self.width, self.height, p.channels), dtype=np.float32)

            if p.channels != image.shape[2]:
                image = image[:, :, 0:p.channels]

            images.append(image.flatten())

        # efficient way to copy all AOV images
        render_passes.foreach_set('rect', np.concatenate(images))
        self.render_engine.end_result(result)

    def _sync_render_settings(self, renderer, scene):
        settings = scene.hdusd.final

        renderer.SetRendererPlugin(settings.delegate)
        if settings.delegate == 'HdRprPlugin':
            hdrpr = settings.hdrpr
            quality = hdrpr.quality
            denoise = hdrpr.denoise

            renderer.SetRendererSetting('renderMode', 'batch')
            renderer.SetRendererSetting('progressive', True)
            renderer.SetRendererSetting('enableAlpha', False)

            renderer.SetRendererSetting('renderDevice', hdrpr.device)
            renderer.SetRendererSetting('renderQuality', hdrpr.render_quality)
            renderer.SetRendererSetting('coreRenderMode', hdrpr.render_mode)

            renderer.SetRendererSetting('aoRadius', hdrpr.ao_radius)

            renderer.SetRendererSetting('maxSamples', hdrpr.max_samples)
            renderer.SetRendererSetting('minAdaptiveSamples', hdrpr.min_adaptive_samples)
            renderer.SetRendererSetting('varianceThreshold', hdrpr.variance_threshold)

            renderer.SetRendererSetting('maxRayDepth', quality.max_ray_depth)
            renderer.SetRendererSetting('maxRayDepthDiffuse', quality.max_ray_depth_diffuse)
            renderer.SetRendererSetting('maxRayDepthGlossy', quality.max_ray_depth_glossy)
            renderer.SetRendererSetting('maxRayDepthRefraction', quality.max_ray_depth_refraction)
            renderer.SetRendererSetting('maxRayDepthGlossyRefraction',
                                        quality.max_ray_depth_glossy_refraction)
            renderer.SetRendererSetting('maxRayDepthShadow', quality.max_ray_depth_shadow)
            renderer.SetRendererSetting('raycastEpsilon', quality.raycast_epsilon)
            renderer.SetRendererSetting('enableRadianceClamping', quality.enable_radiance_clamping)
            renderer.SetRendererSetting('radianceClamping', quality.radiance_clamping)

            renderer.SetRendererSetting('enableDenoising', denoise.enable)
            renderer.SetRendererSetting('denoiseMinIter', denoise.min_iter)
            renderer.SetRendererSetting('denoiseIterStep', denoise.iter_step)


class FinalEngineScene(FinalEngine):
    def _sync(self, depsgraph):
        stage = self.cached_stage.create()

        UsdGeom.SetStageMetersPerUnit(stage, 1)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)

        root_prim = stage.GetPseudoRoot()

        objects_len = sum(1 for _ in object.ObjectData.depsgraph_objects(
                          depsgraph, use_scene_cameras=False))

        for i, obj_data in enumerate(set(object.ObjectData.parent_objects(depsgraph))):
            if self.render_engine.test_break():
                return

            self.notify_status(0.0, f"Syncing object {i}/{objects_len}: {obj_data.object.name}")

            object.sync(root_prim, obj_data)

        for i, obj_data in enumerate(object.ObjectData.depsgraph_objects(
                                     depsgraph, use_scene_cameras=False)):
            if self.render_engine.test_break():
                return

            self.notify_status(0.0, f"Syncing object {i}/{objects_len}: {obj_data.object.name}")

            object.sync(root_prim, obj_data)

        if depsgraph.scene.world is not None:
            world.sync(root_prim, depsgraph.scene.world)

        object.sync(stage.GetPseudoRoot(), object.ObjectData.from_object(depsgraph.scene.camera),
                    scene=depsgraph.scene)


class FinalEngineNodetree(FinalEngine):
    def _sync(self, depsgraph):
        settings = depsgraph.scene.hdusd.final
        output_node = bpy.data.node_groups[settings.data_source].get_output_node()

        if output_node is None:
            log.warn("Syncing stopped due to invalid output_node", output_node)
            return

        stage = output_node.cached_stage()
        self.cached_stage.assign(stage)
