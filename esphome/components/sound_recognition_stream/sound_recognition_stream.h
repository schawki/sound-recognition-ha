#pragma once

#include <atomic>
#include <memory>
#include <string>
#include <vector>

#include "esphome/components/microphone/microphone.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include "esphome/core/component.h"

namespace esphome {
namespace sound_recognition_stream {

// Protocol version 1 (see service/soundrec/espstream.py):
//   device -> "SRESP1" + 16 random bytes          (hello and nonce)
//   service -> HMAC-SHA256(password, nonce)       (32 bytes)
//   device -> 0x01 when the answer is right, otherwise it just closes the connection
//   device -> raw audio, signed 16-bit little-endian, 16 kHz, mono
class SoundRecognitionStream : public Component {
 public:
  void set_microphone(microphone::Microphone *mic) { this->mic_ = mic; }
  void set_password(const std::string &password) { this->password_ = password; }
  void set_port(uint16_t port) { this->port_ = port; }
  void set_gain(float gain) { this->gain_ = gain; }
  void set_info_sensor(text_sensor::TextSensor *sensor) { this->info_ = sensor; }

  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::AFTER_WIFI; }

 protected:
  void on_audio_(const std::vector<uint8_t> &data);   // may run in the microphone task: only fills the ring buffer
  void accept_();
  void check_pending_();
  void drop_client_();
  void stream_();

  microphone::Microphone *mic_{nullptr};
  text_sensor::TextSensor *info_{nullptr};
  std::string password_;
  uint16_t port_{6055};
  float gain_{1.0f};

  int listen_fd_{-1};
  int client_fd_{-1};   // proven client, receives the audio
  int pending_fd_{-1};  // connection that has not proven the password yet (never receives audio)
  uint8_t nonce_[16]{};
  uint8_t answer_[32]{};
  size_t answer_len_{0};
  uint32_t pending_started_{0};

  // Single producer (microphone task), single consumer (main loop): int16 samples.
  std::unique_ptr<int16_t[]> ring_;
  size_t ring_size_{0};
  std::atomic<size_t> head_{0};
  std::atomic<size_t> tail_{0};
  std::atomic<bool> streaming_{false};
  bool mic_started_{false};
};

}  // namespace sound_recognition_stream
}  // namespace esphome
