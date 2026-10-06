"""全部 PNG 滤波的独立编码夹具，核验实际像素摘要和 Alpha。"""
import hashlib
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('rgba_test',ROOT/'skills/effectcraft-use/scripts/image_sequence.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def paeth(a,b,c):
    p=a+b-c; distances=[abs(p-a),abs(p-b),abs(p-c)]
    return (a,b,c)[distances.index(min(distances))]
def png(rows,filters):
    width=len(rows[0])//4; previous=bytes(width*4);scan=bytearray()
    for row,kind in zip(rows,filters):
        scan.append(kind)
        for x,value in enumerate(row):
            left=row[x-4] if x>=4 else 0; above=previous[x]; corner=previous[x-4] if x>=4 else 0
            prediction=(0,left,above,(left+above)//2,paeth(left,above,corner))[kind]
            scan.append((value-prediction)&255)
        previous=row
    def chunk(kind,body):return struct.pack('>I',len(body))+kind+body+struct.pack('>I',zlib.crc32(kind+body))
    return bytes.fromhex('89504e470d0a1a0a')+chunk(b'IHDR',struct.pack('>IIBBBBB',width,len(rows),8,6,0,0,0))+chunk(b'IDAT',zlib.compress(scan))+chunk(b'IEND',b'')
class RgbaFilterTests(unittest.TestCase):
    def test_all_filters_with_wraparound_and_cross_row_dependencies(self):
        rows=[bytes((x*37+y*71)%256 for x in range(32)) for y in range(5)]
        for filters in ([0,1,2,3,4],[4,3,2,1,0],[2]*5,[4]*5):
            with self.subTest(filters=filters), tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'frame.png';path.write_bytes(png(rows,filters));facts=module.rgba_facts(path)
                self.assertEqual(facts['rgbaSha256'],hashlib.sha256(b''.join(rows)).hexdigest())
                alpha=b''.join(row[3::4] for row in rows)
                self.assertEqual(facts['alphaExtrema'],[min(alpha),max(alpha)])
    def test_repeated_zero_residual_rows_keep_pixels(self):
        for row in (bytes(32),bytes([255]*32),bytes([0,255,128,0]*8)):
            for kind in range(5):
                with self.subTest(kind=kind,row=row[:4]), tempfile.TemporaryDirectory() as temp:
                    path=Path(temp)/'frame.png';path.write_bytes(png([row]*3,[kind]*3));facts=module.rgba_facts(path)
                    self.assertEqual(facts['rgbaSha256'],hashlib.sha256(row*3).hexdigest())
