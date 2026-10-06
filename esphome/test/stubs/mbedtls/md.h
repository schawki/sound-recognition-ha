#pragma once
#include <cstdint>
#include <cstddef>
typedef struct mbedtls_md_info_t mbedtls_md_info_t;
enum { MBEDTLS_MD_SHA256 = 1 };
const mbedtls_md_info_t* mbedtls_md_info_from_type(int);
int mbedtls_md_hmac(const mbedtls_md_info_t*, const unsigned char*, size_t, const unsigned char*, size_t, unsigned char*);
