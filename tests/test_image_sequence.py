"""透明序列完整性、实际通道和有界资源检查。"""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sequence', ROOT/'skills/effectcraft-use/scripts/image_sequence.py')
sequence = importlib.util.module_from_spec(spec); spec.loader.exec_module(sequence)


def png(path, color=6, alpha=128):
    def chunk(kind, body):
        return struct.pack('>I', len(body))+kind+body+struct.pack('>I', zlib.crc32(kind+body))
    pixels = bytes([255, 0, 0, alpha, 0, 0, 255, 0]) if color == 6 else bytes([255, 0, 0, 0, 0, 255])
    path.write_bytes(bytes.fromhex('89504e470d0a1a0a')+chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 1, 8, color, 0, 0, 0))+
                    chunk(b'IDAT', zlib.compress(b'\0'+pixels))+chunk(b'IEND', b''))


class SequenceTests(unittest.TestCase):
    def test_frames_record_actual_alpha_and_rational_timing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(2): png(root/f'frame_{index:05d}.png')
            result = sequence.inspect_sequence(root, {'width': 2, 'height': 1, 'frameRate': 4, 'duration': .5})
            self.assertEqual(result['frameCount'], 2)
            self.assertEqual(result['timeBase'], {'num': 1, 'den': 4})
            self.assertEqual(result['frames'][0]['alphaExtrema'], [0, 128])
            self.assertEqual(result['colorSpace'], 'unknown')

    def test_missing_extra_frame_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); comp = {'width': 2, 'height': 1, 'frameRate': 2, 'duration': 1}
            png(root/'frame_00000.png')
            with self.assertRaisesRegex(ValueError, 'sequence_frame_set_mismatch'): sequence.inspect_sequence(root, comp)
            png(root/'frame_00001.png'); png(root/'frame_00002.png')
            with self.assertRaisesRegex(ValueError, 'sequence_frame_set_mismatch'): sequence.inspect_sequence(root, comp)
            (root/'frame_00002.png').unlink(); (root/'frame_00001.png').unlink()
            (root/'frame_00001.png').symlink_to(root/'frame_00000.png')
            with self.assertRaisesRegex(ValueError, 'sequence_frame_invalid'): sequence.inspect_sequence(root, comp)

    def test_rgb_corruption_opaque_and_size_conflict_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); frame = root/'frame_00000.png'; comp = {'width': 2, 'height': 1, 'frameRate': 1, 'duration': 1}
            png(frame, color=2)
            with self.assertRaisesRegex(ValueError, 'sequence_rgba8_required'): sequence.inspect_sequence(root, comp)
            png(frame); data = bytearray(frame.read_bytes()); data[-1] ^= 1; frame.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'provided_png_invalid'): sequence.inspect_sequence(root, comp)
            png(frame); comp['width'] = 3
            with self.assertRaisesRegex(ValueError, 'sequence_dimensions_mismatch'): sequence.inspect_sequence(root, comp)
            png(frame); comp['width'] = 2
            # 两像素均不透明，RGBA 表示不等于透明内容。
            raw = frame.read_bytes(); packed = zlib.compress(b'\0'+bytes([255,0,0,255,0,0,255,255]))
            kind = b'IDAT'; start = raw.index(kind)-4; old_size = struct.unpack_from('>I',raw,start)[0]
            frame.write_bytes(raw[:start]+struct.pack('>I',len(packed))+kind+packed+struct.pack('>I',zlib.crc32(kind+packed))+raw[start+old_size+12:])
            with self.assertRaisesRegex(ValueError, 'sequence_transparency_missing'): sequence.inspect_sequence(root, comp)

    def test_resource_budget_rejects_before_native_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, 'sequence_frame_budget_exceeded'):
                sequence.export_sequence('missing-cli', Path('missing-project'), {'width': 16384, 'height': 16384, 'frameRate': 12, 'duration': 1}, Path(temporary))
            self.assertEqual(list(Path(temporary).iterdir()), [])
