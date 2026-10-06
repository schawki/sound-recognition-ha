#pragma once
#include <cstdint>
#include <functional>
#include <vector>
namespace esphome { namespace audio { struct AudioStreamInfo { size_t samples_to_bytes(size_t n) const { return n * 4; } }; }
namespace microphone {
// Host stand-in: 32-bit samples like an I2S microphone configured with bits_per_sample: 32bit.
class Microphone { public: virtual void start() = 0; virtual void stop() = 0;
  template<typename F> void add_data_callback(F &&f) { cb = f; }
  audio::AudioStreamInfo get_audio_stream_info() { return {}; }
  std::function<void(const std::vector<uint8_t> &)> cb; }; } }
