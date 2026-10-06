// Runs the real device code on a PC (stand-ins for the ESPHome headers in test/stubs, OpenSSL for HMAC) so that the
// Python client can be tested against it. Usage: host_harness <port> <password> <seconds>
// The fake microphone delivers a 32-bit ramp: sample i = (i % 1000) << 16, so the 16-bit stream is i % 1000.
#include <mbedtls/md.h>
#include <esp_random.h>
#include <openssl/hmac.h>
#include <openssl/rand.h>
#include <cstdlib>
#include <cstring>
#include <thread>
#include "sound_recognition_stream.h"

const mbedtls_md_info_t *mbedtls_md_info_from_type(int) { return reinterpret_cast<const mbedtls_md_info_t *>(1); }
int mbedtls_md_hmac(const mbedtls_md_info_t *, const unsigned char *key, size_t klen, const unsigned char *msg, size_t mlen,
                    unsigned char *out) {
  unsigned int n = 0;
  return HMAC(EVP_sha256(), key, (int) klen, msg, mlen, out, &n) ? 0 : -1;
}
void esp_fill_random(void *buf, size_t n) { RAND_bytes((unsigned char *) buf, (int) n); }

struct FakeMic : esphome::microphone::Microphone {
  bool running = false;
  void start() override { running = true; }
  void stop() override { running = false; }
};

int main(int argc, char **argv) {
  using namespace esphome::sound_recognition_stream;
  FakeMic mic;
  SoundRecognitionStream s;
  esphome::text_sensor::TextSensor info;
  s.set_microphone(&mic);
  s.set_password(argv[2]);
  s.set_port(atoi(argv[1]));
  s.set_info_sensor(&info);
  s.setup();
  const int seconds = atoi(argv[3]);
  uint32_t counter = 0;
  auto end = std::chrono::steady_clock::now() + std::chrono::seconds(seconds);
  while (std::chrono::steady_clock::now() < end) {
    s.loop();
    if (mic.running) {
      std::vector<uint8_t> data(160 * 4);
      for (int i = 0; i < 160; i++) {
        int32_t v = (int32_t) ((counter++ % 1000) << 16);
        std::memcpy(data.data() + i * 4, &v, 4);
      }
      mic.cb(data);
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
  return 0;
}
