import struct
import base64


ULAW_TABLE = [
    -32124, -31100, -30076, -29052, -28028, -27004, -25980, -24956,
    -23932, -22908, -21884, -20860, -19836, -18812, -17788, -16764,
    -15996, -15484, -14972, -14460, -13948, -13436, -12924, -12412,
    -11900, -11388, -10876, -10364, -9852, -9340, -8828, -8316,
    -7932, -7676, -7420, -7164, -6908, -6652, -6396, -6140,
    -5884, -5628, -5372, -5116, -4860, -4604, -4348, -4092,
    -3900, -3772, -3644, -3516, -3388, -3260, -3132, -3004,
    -2876, -2748, -2620, -2492, -2364, -2236, -2108, -1980,
    -1884, -1820, -1756, -1692, -1628, -1564, -1500, -1436,
    -1372, -1308, -1244, -1180, -1116, -1052, -988, -924,
    -876, -844, -812, -780, -748, -716, -684, -652,
    -620, -588, -556, -524, -492, -460, -428, -396,
    -372, -356, -340, -324, -308, -292, -276, -260,
    -244, -228, -212, -196, -180, -164, -148, -132,
    -120, -112, -104, -96, -88, -80, -72, -64,
    -56, -48, -40, -32, -24, -16, -8, 0,
    32124, 31100, 30076, 29052, 28028, 27004, 25980, 24956,
    23932, 22908, 21884, 20860, 19836, 18812, 17788, 16764,
    15996, 15484, 14972, 14460, 13948, 13436, 12924, 12412,
    11900, 11388, 10876, 10364, 9852, 9340, 8828, 8316,
    7932, 7676, 7420, 7164, 6908, 6652, 6396, 6140,
    5884, 5628, 5372, 5116, 4860, 4604, 4348, 4092,
    3900, 3772, 3644, 3516, 3388, 3260, 3132, 3004,
    2876, 2748, 2620, 2492, 2364, 2236, 2108, 1980,
    1884, 1820, 1756, 1692, 1628, 1564, 1500, 1436,
    1372, 1308, 1244, 1180, 1116, 1052, 988, 924,
    876, 844, 812, 780, 748, 716, 684, 652,
    620, 588, 556, 524, 492, 460, 428, 396,
    372, 356, 340, 324, 308, 292, 276, 260,
    244, 228, 212, 196, 180, 164, 148, 132,
    120, 112, 104, 96, 88, 80, 72, 64,
    56, 48, 40, 32, 24, 16, 8, 0
]


def ulaw_to_pcm16(ulaw_bytes):
    pcm_samples = []
    for byte in ulaw_bytes:
        pcm_samples.append(ULAW_TABLE[byte])
    return struct.pack('<' + 'h' * len(pcm_samples), *pcm_samples)


def pcm16_to_ulaw(pcm_bytes):
    ulaw_bytes = []
    for i in range(0, len(pcm_bytes), 2):
        sample = struct.unpack('<h', pcm_bytes[i:i+2])[0]
        ulaw_bytes.append(linear_to_ulaw(sample))
    return bytes(ulaw_bytes)


def linear_to_ulaw(sample):
    BIAS = 0x84
    CLIP = 32635
    sign = 0
    if sample < 0:
        sign = 0x80
        sample = -sample
    if sample > CLIP:
        sample = CLIP
    sample = sample + BIAS
    exponent = 7
    for exp_mask in [0x4000, 0x2000, 0x1000, 0x800, 0x400, 0x200, 0x100]:
        if sample & exp_mask:
            break
        exponent -= 1
    mantissa = (sample >> (exponent + 3)) & 0x0F
    ulaw_byte = ~(sign | (exponent << 4) | mantissa)
    return ulaw_byte & 0xFF


def base64_ulaw_to_pcm16(base64_ulaw):
    ulaw_bytes = base64.b64decode(base64_ulaw)
    return ulaw_to_pcm16(ulaw_bytes)


def pcm16_to_base64_ulaw(pcm_bytes):
    ulaw_bytes = pcm16_to_ulaw(pcm_bytes)
    return base64.b64encode(ulaw_bytes).decode('utf-8')


class AudioBuffer:
    def __init__(self, sample_rate=8000):
        self.sample_rate = sample_rate
        self.buffer = bytearray()

    def add_chunk(self, chunk):
        self.buffer.extend(chunk)

    def get_all(self):
        return bytes(self.buffer)

    def clear(self):
        self.buffer = bytearray()

    def get_duration_ms(self):
        return (len(self.buffer) / self.sample_rate) * 1000
