"""PaddleOCR PP-OCRv4 CPU inference; no downloads or training components.

DB postprocessing derives from Apache-2.0 PaddleOCR, with its optional
Paddle Tensor conversion removed; both predictors already return NumPy arrays.
The preprocessing and CTC decoding follow PaddleOCR's inference pipeline.
"""
from __future__ import annotations

import math
import os
from pathlib import Path

import cv2
import numpy as np

from .third_party.db_postprocess import DBPostProcess

_allocator_registered = False


def shared_cpu_allocator(ort):
    """Reuse scratch space across the three serial OCR sessions, not weights."""
    global _allocator_registered
    if _allocator_registered:
        return
    info = ort.OrtMemoryInfo('Cpu',ort.OrtAllocatorType.ORT_ARENA_ALLOCATOR,0,ort.OrtMemType.DEFAULT)
    config = ort.OrtArenaCfg({'max_mem':0,'arena_extend_strategy':0,
                            'initial_chunk_size_bytes':32*1024*1024,
                            'initial_growth_chunk_size_bytes':1024*1024,
                            'max_dead_bytes_per_chunk':1024*1024})
    ort.create_and_register_allocator(info,config)
    _allocator_registered = True


class Predictor:
    def __init__(self, folder):
        self.session = None
        names = {'det':'ch_PP-OCRv4_det_infer.onnx', 'rec':'ch_PP-OCRv4_rec_infer.onnx',
                 'cls':'ch_ppocr_mobile_v2.0_cls_infer.onnx'}
        onnx = folder.parent / 'onnx' / names[folder.name]
        if onnx.is_file() and os.environ.get('DEEPPICK_BACKEND', 'onnx') != 'paddle':
            import onnxruntime as ort
            shared_cpu_allocator(ort)
            options = ort.SessionOptions()
            options.intra_op_num_threads = 4
            options.inter_op_num_threads = 1
            options.add_session_config_entry('session.intra_op.allow_spinning', '0')
            options.add_session_config_entry('session.inter_op.allow_spinning', '0')
            options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            options.enable_mem_pattern = False
            options.add_session_config_entry('session.use_env_allocators','1')
            options.add_session_config_entry('session.use_device_allocator_for_initializers','1')
            self.run_options = ort.RunOptions()
            self.run_options.add_run_config_entry('memory.enable_memory_arena_shrinkage','cpu:0')
            self.session = ort.InferenceSession(onnx.read_bytes(), options, providers=['CPUExecutionProvider'])
            self.input_name = self.session.get_inputs()[0].name
            return
        from paddle import inference
        model, params = folder / "inference.pdmodel", folder / "inference.pdiparams"
        if not model.is_file() or not params.is_file():
            raise RuntimeError("离线 OCR 模型缺失，请恢复 models 文件夹后重试。")
        # Paddle's C++ file loader cannot open some Chinese Windows paths.
        # Loading bytes also works when the portable package is moved on D:.
        self.model_bytes = model.read_bytes()
        self.param_bytes = params.read_bytes()
        config = inference.Config()
        config.set_model_buffer(self.model_bytes,len(self.model_bytes),self.param_bytes,len(self.param_bytes))
        config.disable_gpu()
        config.set_cpu_math_library_num_threads(4)
        config.disable_glog_info()
        config.enable_memory_optim()
        config.switch_ir_optim(True)
        config.switch_use_feed_fetch_ops(False)
        if os.environ.get("DEEPPICK_MKLDNN", "1") == "1":
            config.enable_mkldnn()
            config.set_mkldnn_cache_capacity(8)
        self.predictor = inference.create_predictor(config)
        self.input = self.predictor.get_input_handle(self.predictor.get_input_names()[0])
        self.output = self.predictor.get_output_handle(self.predictor.get_output_names()[0])

    def run(self, array):
        if self.session is not None:
            return self.session.run(None, {self.input_name:np.ascontiguousarray(array,dtype=np.float32)},self.run_options)[0]
        self.input.reshape(array.shape)
        self.input.copy_from_cpu(np.ascontiguousarray(array, dtype=np.float32))
        self.predictor.run()
        return self.output.copy_to_cpu()


class PaddleEngine:
    def __init__(self, models: Path):
        cv2.setNumThreads(4)
        self.det = Predictor(models / "det")
        self.rec = Predictor(models / "rec")
        self.cls = Predictor(models / "cls")
        dictionary = (models / "ppocr_keys_v1.txt").read_text("utf-8").splitlines()
        self.characters = [""] + dictionary + [" "]
        self.post = DBPostProcess(thresh=.3, box_thresh=.5, max_candidates=2000,
                                  unclip_ratio=1.5, score_mode="fast", box_type="quad")

    def warmup(self):
        self.det.run(np.zeros((1, 3, 64, 64), dtype=np.float32))
        self.rec.run(np.zeros((1, 3, 48, 320), dtype=np.float32))
        self.cls.run(np.zeros((1, 3, 48, 192), dtype=np.float32))

    def release_scratch(self):
        # A tiny run returns free arena chunks after previous output views die.
        # Model sessions, packed weights and thread pools remain ready.
        if self.det.session is not None:
            self.det.run(np.zeros((1,3,64,64),dtype=np.float32))

    @staticmethod
    def crop(image, polygon):
        p = np.asarray(polygon, dtype=np.float32)
        width = max(2, round(max(np.linalg.norm(p[0]-p[1]), np.linalg.norm(p[2]-p[3]))))
        height = max(2, round(max(np.linalg.norm(p[0]-p[3]), np.linalg.norm(p[1]-p[2]))))
        dest = np.array([[0,0],[width,0],[width,height],[0,height]], dtype=np.float32)
        matrix = cv2.getPerspectiveTransform(p, dest)
        crop = cv2.warpPerspective(image, matrix, (width,height), flags=cv2.INTER_CUBIC,
                                   borderMode=cv2.BORDER_REPLICATE)
        return np.rot90(crop).copy() if height/max(1,width) >= 1.5 else crop

    @staticmethod
    def normalize_crop(image, width, height, output=None):
        new_width = min(width, math.ceil(height*image.shape[1]/image.shape[0]))
        resized = cv2.resize(image, (max(1,new_width),height)).astype(np.float32)
        resized /= 255.
        resized -= .5
        resized /= .5
        normalized = resized.transpose(2,0,1)
        padded = np.zeros((3,height,width),dtype=np.float32) if output is None else output
        padded[:,:,:new_width] = normalized
        return padded

    def recognize(self, path):
        # imdecode, unlike cv2.imread, supports non-ASCII Windows paths.
        image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError("截图文件无法读取，请重新截图。")
        return self.recognize_array(image)

    def recognize_array(self, image):
        image, offset_x, offset_y = self._trim_border(image)
        h, w = image.shape[:2]
        if h*w > 40_000_000:
            raise RuntimeError("截图过大，请分成多个区域识别。")
        ratio = min(1., 1920/max(h,w))
        dh = max(32, round(h*ratio/32)*32)
        dw = max(32, round(w*ratio/32)*32)
        data = cv2.resize(image, (dw,dh)).astype(np.float32)
        data /= 255.
        data -= np.array([.485,.456,.406],dtype=np.float32)
        data /= np.array([.229,.224,.225],dtype=np.float32)
        prediction = self.det.run(data.transpose(2,0,1)[None])
        polygons = self.post({"maps": prediction}, np.array([[h,w,dh/h,dw/w]]))[0]["points"]
        del prediction,data
        candidates = []
        for poly in polygons:
            poly = np.asarray(poly, dtype=np.float32)
            poly[:,0] = np.clip(poly[:,0],0,w-1)
            poly[:,1] = np.clip(poly[:,1],0,h-1)
            if np.linalg.norm(poly[0]-poly[1]) < 3 or np.linalg.norm(poly[0]-poly[3]) < 3:
                continue
            candidates.append((poly, self.crop(image, poly)))
        if len(candidates) > 2000:
            raise RuntimeError("文字区域过多，请缩小截图范围。")
        # Angle classification keeps upside-down text usable.
        for start in range(0,len(candidates),8):
            batch = candidates[start:start+8]
            cls_images = np.zeros((len(batch),3,48,192),dtype=np.float32)
            for index,(_,crop) in enumerate(batch):
                self.normalize_crop(crop,192,48,cls_images[index])
            cls_result = self.cls.run(cls_images)
            for index, result in enumerate(cls_result):
                if int(result.argmax()) == 1 and float(result.max()) > .9:
                    polygon, crop = candidates[start+index]
                    candidates[start+index] = polygon, cv2.rotate(crop, cv2.ROTATE_180)
            del cls_images,cls_result,result
        blocks = []
        # Similar aspect ratios are batched together to limit padded allocations.
        candidates.sort(key=lambda item: item[1].shape[1]/item[1].shape[0])
        for start in range(0,len(candidates),6):
            batch = candidates[start:start+6]
            width = min(4096, max(320, math.ceil(max(c.shape[1]/c.shape[0] for _,c in batch)*48)))
            rec_images = np.zeros((len(batch),3,48,width),dtype=np.float32)
            for index,(_,crop) in enumerate(batch):
                self.normalize_crop(crop,width,48,rec_images[index])
            results = self.rec.run(rec_images)
            for (polygon,_), output in zip(batch,results):
                indices = output.argmax(axis=1)
                scores = output.max(axis=1)
                chars, kept_scores, previous = [], [], -1
                for index, score in zip(indices,scores):
                    index = int(index)
                    if index != 0 and index != previous and index < len(self.characters):
                        chars.append(self.characters[index])
                        kept_scores.append(float(score))
                    previous = index
                text = "".join(chars)
                if not text.strip():
                    continue
                polygon += np.array([offset_x,offset_y],dtype=np.float32)
                x, y = polygon.min(axis=0)
                right, bottom = polygon.max(axis=0)
                blocks.append({"text":text, "x":float(x), "y":float(y),
                               "width":float(right-x), "height":float(bottom-y),
                               "confidence":sum(kept_scores)/max(1,len(kept_scores)),
                               "polygon":polygon.tolist(), "source":"local"})
            del rec_images,results,output,indices,scores
        return blocks

    @staticmethod
    def _trim_border(image):
        """Remove only near-uniform exterior padding, keeping a margin around ink."""
        h,w = image.shape[:2]
        if h*w > 40_000_000:
            raise RuntimeError('截图过大，请分成多个区域识别。')
        edge = np.concatenate((image[0],image[-1],image[:,0],image[:,-1]))
        color = np.median(edge,axis=0)
        difference = np.max(np.abs(edge.astype(np.int16)-color),axis=1)
        if np.mean(difference <= 3) < .98:
            return image,0,0
        lower = tuple(float(np.ceil(value-3)) for value in color)
        upper = tuple(float(np.floor(value+3)) for value in color)
        inside = cv2.inRange(image,lower,upper)
        rows = np.flatnonzero(inside.min(axis=1)==0)
        cols = np.flatnonzero(inside.min(axis=0)==0)
        if not len(rows) or not len(cols):
            return image[:min(h,64),:min(w,64)],0,0
        left,top = max(0,int(cols[0])-12),max(0,int(rows[0])-12)
        right,bottom = min(w,int(cols[-1])+13),min(h,int(rows[-1])+13)
        if (right-left)*(bottom-top) > h*w*.85:
            return image,0,0
        return image[top:bottom,left:right],left,top
