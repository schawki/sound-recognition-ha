#pragma once
#include <cstdio>
#define ESP_LOGE(t,...) printf(__VA_ARGS__)
#define ESP_LOGW(t,...) printf(__VA_ARGS__)
#define ESP_LOGI(t,...) printf(__VA_ARGS__)
#define ESP_LOGCONFIG(t,...) printf(__VA_ARGS__)
