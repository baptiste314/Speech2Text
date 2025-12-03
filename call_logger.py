import os
import json
import wave
import struct
import datetime
from pathlib import Path
from audio_utils import base64_ulaw_to_pcm16


class CallLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.call_id = None
        self.call_start = None
        self.combined_audio = []
        self.events = []
        self.current_timestamp_ms = 0
        self.ai_audio_position_ms = 0
        self.ai_response_start_ms = None

    def start_call(self, stream_sid):
        self.call_id = stream_sid
        self.call_start = datetime.datetime.now()
        self.combined_audio = []
        self.events = []
        self.current_timestamp_ms = 0
        self.ai_audio_position_ms = 0
        self.ai_response_start_ms = None
        self._log_event("call_started", {"stream_sid": stream_sid})

    def log_incoming_audio(self, base64_payload, timestamp_ms=None):
        try:
            pcm_data = base64_ulaw_to_pcm16(base64_payload)
            if timestamp_ms is not None:
                self.current_timestamp_ms = timestamp_ms
            self.combined_audio.append({
                "timestamp": self.current_timestamp_ms,
                "source": "user",
                "data": pcm_data
            })
        except Exception as e:
            self._log_event("audio_decode_error", {"error": str(e), "direction": "incoming"})

    def log_outgoing_audio(self, base64_payload):
        try:
            pcm_data = base64_ulaw_to_pcm16(base64_payload)
            sample_rate = 8000
            bytes_per_sample = 2
            
            if self.ai_response_start_ms is None:
                self.ai_response_start_ms = self.current_timestamp_ms
                self.ai_audio_position_ms = self.ai_response_start_ms
            
            self.combined_audio.append({
                "timestamp": self.ai_audio_position_ms,
                "source": "ai",
                "data": pcm_data
            })
            
            chunk_duration_ms = (len(pcm_data) // bytes_per_sample) * 1000 // sample_rate
            self.ai_audio_position_ms += chunk_duration_ms
            
        except Exception as e:
            self._log_event("audio_decode_error", {"error": str(e), "direction": "outgoing"})

    def reset_ai_response(self):
        self.ai_response_start_ms = None
        self.ai_audio_position_ms = 0

    def log_transcription(self, text, role="user"):
        self._log_event("transcription", {"role": role, "text": text})

    def log_ai_response(self, text):
        self._log_event("ai_response", {"text": text})

    def _log_event(self, event_type, data):
        event = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": event_type,
            "data": data
        }
        self.events.append(event)

    def end_call(self):
        if not self.call_id:
            return
        
        call_dir = self.log_dir / f"call_{self.call_id}_{self.call_start.strftime('%Y%m%d_%H%M%S')}"
        call_dir.mkdir(exist_ok=True)

        if self.combined_audio:
            combined_pcm = self._mix_audio_streams()
            self._save_wav(call_dir / "call_recording.wav", combined_pcm)

        with open(call_dir / "events.json", "w", encoding="utf-8") as f:
            json.dump(self.events, f, indent=2, ensure_ascii=False)

        self._log_event("call_ended", {"duration_events": len(self.events)})
        
        self.call_id = None
        self.combined_audio = []
        self.events = []

    def _mix_audio_streams(self):
        if not self.combined_audio:
            return b''
        
        sample_rate = 8000
        bytes_per_sample = 2
        
        sorted_chunks = sorted(self.combined_audio, key=lambda x: x["timestamp"])
        
        max_timestamp = sorted_chunks[-1]["timestamp"]
        last_chunk = sorted_chunks[-1]["data"]
        total_duration_ms = max_timestamp + (len(last_chunk) // bytes_per_sample) * 1000 // sample_rate
        total_samples = int((total_duration_ms / 1000) * sample_rate) + sample_rate
        
        mixed_samples = [0] * total_samples
        
        for chunk in sorted_chunks:
            start_sample = int((chunk["timestamp"] / 1000) * sample_rate)
            pcm_data = chunk["data"]
            
            num_samples = len(pcm_data) // bytes_per_sample
            for i in range(num_samples):
                if start_sample + i < total_samples:
                    sample = struct.unpack('<h', pcm_data[i*2:(i+1)*2])[0]
                    mixed_samples[start_sample + i] += sample
        
        output = bytearray()
        for sample in mixed_samples:
            clamped = max(-32768, min(32767, sample))
            output.extend(struct.pack('<h', clamped))
        
        return bytes(output)

    def _save_wav(self, filepath, pcm_data, sample_rate=8000, channels=1, sample_width=2):
        with wave.open(str(filepath), 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)
