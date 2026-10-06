#include "sound_recognition_stream.h"

#ifdef USE_ESP32

#include <fcntl.h>
#include <lwip/sockets.h>
#include <mbedtls/md.h>
#include <esp_random.h>
#include <cerrno>
#include <cstring>

#include "esphome/core/hal.h"
#include "esphome/core/log.h"

namespace esphome {
namespace sound_recognition_stream {

static const char *const TAG = "sound_recognition_stream";
static const char MAGIC[6] = {'S', 'R', 'E', 'S', 'P', '1'};
static const uint32_t ANSWER_TIMEOUT_MS = 5000;
static const size_t RING_SAMPLES = 16000;  // one second

static bool hmac_sha256(const std::string &key, const uint8_t *msg, size_t len, uint8_t out[32]) {
  const mbedtls_md_info_t *info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  return info != nullptr &&
         mbedtls_md_hmac(info, reinterpret_cast<const uint8_t *>(key.data()), key.size(), msg, len, out) == 0;
}

static bool equal_constant_time(const uint8_t *a, const uint8_t *b, size_t n) {
  uint8_t diff = 0;
  for (size_t i = 0; i < n; i++) diff |= a[i] ^ b[i];
  return diff == 0;
}

void SoundRecognitionStream::setup() {
  this->ring_size_ = RING_SAMPLES;
  this->ring_.reset(new (std::nothrow) int16_t[this->ring_size_]);
  if (!this->ring_) {
    ESP_LOGE(TAG, "not enough memory for the audio buffer");
    this->mark_failed();
    return;
  }

  this->listen_fd_ = ::socket(AF_INET, SOCK_STREAM, IPPROTO_IP);
  if (this->listen_fd_ < 0) {
    ESP_LOGE(TAG, "cannot create the socket (errno %d)", errno);
    this->mark_failed();
    return;
  }
  int yes = 1;
  ::setsockopt(this->listen_fd_, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
  ::fcntl(this->listen_fd_, F_SETFL, ::fcntl(this->listen_fd_, F_GETFL, 0) | O_NONBLOCK);
  struct sockaddr_in addr {};
  addr.sin_family = AF_INET;
  addr.sin_addr.s_addr = htonl(INADDR_ANY);
  addr.sin_port = htons(this->port_);
  if (::bind(this->listen_fd_, reinterpret_cast<struct sockaddr *>(&addr), sizeof(addr)) != 0 ||
      ::listen(this->listen_fd_, 1) != 0) {
    ESP_LOGE(TAG, "cannot listen on port %u (errno %d)", this->port_, errno);
    this->mark_failed();
    return;
  }

  this->mic_->add_data_callback([this](const std::vector<uint8_t> &data) { this->on_audio_(data); });
  if (this->info_ != nullptr) this->info_->publish_state("sound-recognition-stream/1 port=" + std::to_string(this->port_));
}

void SoundRecognitionStream::dump_config() {
  ESP_LOGCONFIG(TAG, "Sound Recognition stream:\n  Port: %u\n  Gain: %.2f\n  Password: set (%u characters)", this->port_,
                this->gain_, (unsigned) this->password_.size());
}

// Converts what the microphone delivers (16 or 32 bits) to 16-bit mono at the configured gain and queues it.
void SoundRecognitionStream::on_audio_(const std::vector<uint8_t> &data) {
  if (!this->streaming_.load()) return;  // nobody listens: nothing is kept
  auto info = this->mic_->get_audio_stream_info();
  const size_t bytes_per_sample = info.samples_to_bytes(1);
  const size_t n = bytes_per_sample ? data.size() / bytes_per_sample : 0;
  size_t head = this->head_.load(std::memory_order_relaxed);
  const size_t tail = this->tail_.load(std::memory_order_acquire);
  for (size_t i = 0; i < n; i++) {
    int32_t v;
    if (bytes_per_sample == 4) {
      int32_t s;
      std::memcpy(&s, data.data() + i * 4, 4);
      v = s >> 16;  // the top 16 bits of the 24-bit sample (INMP441)
    } else {
      int16_t s;
      std::memcpy(&s, data.data() + i * 2, 2);
      v = s;
    }
    if (this->gain_ != 1.0f) {
      float f = v * this->gain_;
      v = f > 32767.0f ? 32767 : (f < -32768.0f ? -32768 : (int32_t) f);
    }
    const size_t next = (head + 1) % this->ring_size_;
    if (next == tail) {  // full: the client is too slow, drop the newest samples
      continue;
    }
    this->ring_[head] = (int16_t) v;
    head = next;
  }
  this->head_.store(head, std::memory_order_release);
}

void SoundRecognitionStream::drop_client_() {
  this->streaming_.store(false);
  if (this->client_fd_ >= 0) ::close(this->client_fd_);
  this->client_fd_ = -1;
  this->tail_.store(this->head_.load());
  if (this->mic_started_) {
    this->mic_->stop();
    this->mic_started_ = false;
  }
}

// Every new connection waits in the pending slot until it proves it knows the password. It never disturbs the connection
// that is streaming, and never receives audio before it has proven it. One pending connection at a time (5 s at most).
void SoundRecognitionStream::accept_() {
  struct sockaddr_in peer {};
  socklen_t len = sizeof(peer);
  int fd = ::accept(this->listen_fd_, reinterpret_cast<struct sockaddr *>(&peer), &len);
  if (fd < 0) return;
  if (this->pending_fd_ >= 0) {
    ::close(fd);
    return;
  }
  int nodelay = 1;
  ::setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &nodelay, sizeof(nodelay));
  ::fcntl(fd, F_SETFL, ::fcntl(fd, F_GETFL, 0) | O_NONBLOCK);
  this->pending_fd_ = fd;
  this->pending_started_ = millis();
  this->answer_len_ = 0;
  esp_fill_random(this->nonce_, sizeof(this->nonce_));
  uint8_t hello[sizeof(MAGIC) + sizeof(this->nonce_)];
  std::memcpy(hello, MAGIC, sizeof(MAGIC));
  std::memcpy(hello + sizeof(MAGIC), this->nonce_, sizeof(this->nonce_));
  ::send(fd, hello, sizeof(hello), 0);
}

void SoundRecognitionStream::check_pending_() {
  if (this->pending_fd_ < 0) return;
  if (millis() - this->pending_started_ > ANSWER_TIMEOUT_MS) {
    ::close(this->pending_fd_);
    this->pending_fd_ = -1;
    return;
  }
  while (this->answer_len_ < sizeof(this->answer_)) {
    int r = ::recv(this->pending_fd_, this->answer_ + this->answer_len_, sizeof(this->answer_) - this->answer_len_, 0);
    if (r > 0) {
      this->answer_len_ += r;
    } else if (r == 0 || (errno != EAGAIN && errno != EWOULDBLOCK)) {
      ::close(this->pending_fd_);
      this->pending_fd_ = -1;
      return;
    } else {
      return;  // not complete yet
    }
  }
  uint8_t expected[32];
  const bool good = hmac_sha256(this->password_, this->nonce_, sizeof(this->nonce_), expected) &&
                    equal_constant_time(expected, this->answer_, sizeof(expected));
  if (!good) {
    ESP_LOGW(TAG, "a client gave a wrong password; connection closed");
    ::close(this->pending_fd_);
    this->pending_fd_ = -1;
    return;
  }
  // Proven: it replaces the previous client (a service that restarted must be able to come back at once).
  const int fd = this->pending_fd_;
  this->pending_fd_ = -1;
  if (this->client_fd_ >= 0) ::close(this->client_fd_);
  this->client_fd_ = fd;
  const uint8_t ok = 0x01;
  ::send(fd, &ok, 1, 0);
  this->tail_.store(this->head_.load());
  this->streaming_.store(true);
  if (!this->mic_started_) {
    this->mic_->start();
    this->mic_started_ = true;
  }
  ESP_LOGI(TAG, "client connected, streaming");
}

void SoundRecognitionStream::stream_() {
  // A closed connection is noticed by recv() returning 0 (the service sends nothing after its answer).
  uint8_t dummy;
  int r = ::recv(this->client_fd_, &dummy, 1, 0);
  if (r == 0 || (r < 0 && errno != EAGAIN && errno != EWOULDBLOCK)) {
    ESP_LOGI(TAG, "client left");
    this->drop_client_();
    return;
  }
  size_t tail = this->tail_.load(std::memory_order_relaxed);
  const size_t head = this->head_.load(std::memory_order_acquire);
  while (tail != head) {
    const size_t until = head > tail ? head : this->ring_size_;  // contiguous part
    const size_t bytes = (until - tail) * sizeof(int16_t);
    int sent = ::send(this->client_fd_, this->ring_.get() + tail, bytes, 0);
    if (sent > 0) {
      size_t done = sent;
      while (done % sizeof(int16_t) != 0) {  // half a sample went out: finish it so the stream stays aligned
        int more = ::send(this->client_fd_, reinterpret_cast<const uint8_t *>(this->ring_.get() + tail) + done, 1, 0);
        if (more > 0) done += more;
        else break;
      }
      tail = (tail + done / sizeof(int16_t)) % this->ring_size_;
    } else if (sent < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
      break;
    } else {
      ESP_LOGI(TAG, "client lost");
      this->drop_client_();
      return;
    }
  }
  if (this->streaming_.load()) this->tail_.store(tail, std::memory_order_release);
}

void SoundRecognitionStream::loop() {
  if (this->listen_fd_ < 0) return;
  this->accept_();
  this->check_pending_();
  if (this->client_fd_ >= 0) this->stream_();
}

}  // namespace sound_recognition_stream
}  // namespace esphome

#endif  // USE_ESP32
