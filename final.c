#include <stdint.h>
#include <stdio.h>
/*
extern uint32_t getKeya();
extern uint32_t getKeyb();
extern uint32_t getKeyc();
extern uint32_t getKeyd();
extern uint32_t getLen();
*/

static void base255_all(const char* str, uint32_t* a, uint32_t* b, uint32_t* c, uint32_t* d) {
    uint32_t w0 = 0, w1 = 0, w2 = 0, w3 = 0;

    const unsigned char* s = (const unsigned char*)str;
    while (*s != 0) {
        uint32_t byte = (uint32_t)(*s++);
        uint64_t v0 = (uint64_t)w0 * 255u + byte;
        w0 = (uint32_t)v0;
        uint64_t carry = v0 >> 32;

        uint64_t v1 = (uint64_t)w1 * 255u + carry;
        w1 = (uint32_t)v1;
        carry = v1 >> 32;

        uint64_t v2 = (uint64_t)w2 * 255u + carry;
        w2 = (uint32_t)v2;
        carry = v2 >> 32;

        uint64_t v3 = (uint64_t)w3 * 255u + carry;
        w3 = (uint32_t)v3;
    }

    *a = w0; *b = w1; *c = w2; *d = w3;
}

uint32_t conv_a(const char* str) { uint32_t a,b,c,d; base255_all(str,&a,&b,&c,&d); return a; }
uint32_t conv_b(const char* str) { uint32_t a,b,c,d; base255_all(str,&a,&b,&c,&d); return b; }
uint32_t conv_c(const char* str) { uint32_t a,b,c,d; base255_all(str,&a,&b,&c,&d); return c; }
uint32_t conv_d(const char* str) { uint32_t a,b,c,d; base255_all(str,&a,&b,&c,&d); return d; }


static inline uint32_t rotr32(uint32_t x, uint32_t n) {
    return (x >> n) | (x << (32 - n));
}
static inline uint32_t bswap32(uint32_t x) {
    return (x >> 24) |
           ((x >> 8) & 0x0000FF00u) |
           ((x << 8) & 0x00FF0000u) |
           (x << 24);
}
#define LICENCE0 0x2378d00bu
#define LICENCE1 0x37ab75a6u
#define LICENCE2 0xfe147e15u
#define LICENCE3 0x878f8ec2u
#define CH(x,y,z)  ((x & y) ^ (~x & z))
#define MAJ(x,y,z) ((x & y) ^ (x & z) ^ (y & z))
#define EP0(x)     (rotr32(x,2) ^ rotr32(x,13) ^ rotr32(x,22))
#define EP1(x)     (rotr32(x,6) ^ rotr32(x,11) ^ rotr32(x,25))
#define SIG0(x)    (rotr32(x,7) ^ rotr32(x,18) ^ (x >> 3))
#define SIG1(x)    (rotr32(x,17) ^ rotr32(x,19) ^ (x >> 10))

#define RND(a,b,c,d,e,f,g,h,k,w) \
    do { \
        uint32_t t1 = (h) + EP1(e) + CH(e,f,g) + (k) + (w); \
        uint32_t t2 = EP0(a) + MAJ(a,b,c); \
        (d) += t1; \
        (h) = t1 + t2; \
    } while(0)

#define PMIX(c0,c1) \
    do { \
        a += rotr32(e ^ (c0), 5); \
        b ^= rotr32(f + (c1), 7); \
        c += rotr32(g ^ a, 11); \
        d ^= rotr32(h + b, 13); \
        e += rotr32(a ^ d, 17); \
        f ^= rotr32(b + c, 19); \
        g += rotr32(c ^ e, 23); \
        h ^= rotr32(d + f, 27); \
        uint32_t t = a; a = c; c = t; \
        t = b; b = d; d = t; \
        t = e; e = g; g = t; \
        t = f; f = h; h = t; \
    } while(0)

#define HASH(a_in,b_in,c_in,d_in, A,B,C,D) \
    do { \
        uint32_t w0  = bswap32(a_in); \
        uint32_t w1  = bswap32(b_in); \
        uint32_t w2  = bswap32(c_in); \
        uint32_t w3  = bswap32(d_in); \
        uint32_t w4  = 0x80000000u; \
        uint32_t w5  = 0; \
        uint32_t w6  = 0; \
        uint32_t w7  = 0; \
        uint32_t w8  = 0; \
        uint32_t w9  = 0; \
        uint32_t w10 = 0; \
        uint32_t w11 = 0; \
        uint32_t w12 = 0; \
        uint32_t w13 = 0; \
        uint32_t w14 = 0; \
        uint32_t w15 = 128u; \
        \
        uint32_t w16 = SIG1(w14) + w9  + SIG0(w1)  + w0; \
        uint32_t w17 = SIG1(w15) + w10 + SIG0(w2)  + w1; \
        uint32_t w18 = SIG1(w16) + w11 + SIG0(w3)  + w2; \
        uint32_t w19 = SIG1(w17) + w12 + SIG0(w4)  + w3; \
        uint32_t w20 = SIG1(w18) + w13 + SIG0(w5)  + w4; \
        uint32_t w21 = SIG1(w19) + w14 + SIG0(w6)  + w5; \
        uint32_t w22 = SIG1(w20) + w15 + SIG0(w7)  + w6; \
        uint32_t w23 = SIG1(w21) + w16 + SIG0(w8)  + w7; \
        uint32_t w24 = SIG1(w22) + w17 + SIG0(w9)  + w8; \
        uint32_t w25 = SIG1(w23) + w18 + SIG0(w10) + w9; \
        uint32_t w26 = SIG1(w24) + w19 + SIG0(w11) + w10; \
        uint32_t w27 = SIG1(w25) + w20 + SIG0(w12) + w11; \
        uint32_t w28 = SIG1(w26) + w21 + SIG0(w13) + w12; \
        uint32_t w29 = SIG1(w27) + w22 + SIG0(w14) + w13; \
        uint32_t w30 = SIG1(w28) + w23 + SIG0(w15) + w14; \
        uint32_t w31 = SIG1(w29) + w24 + SIG0(w16) + w15; \
        uint32_t w32 = SIG1(w30) + w25 + SIG0(w17) + w16; \
        uint32_t w33 = SIG1(w31) + w26 + SIG0(w18) + w17; \
        uint32_t w34 = SIG1(w32) + w27 + SIG0(w19) + w18; \
        uint32_t w35 = SIG1(w33) + w28 + SIG0(w20) + w19; \
        uint32_t w36 = SIG1(w34) + w29 + SIG0(w21) + w20; \
        uint32_t w37 = SIG1(w35) + w30 + SIG0(w22) + w21; \
        uint32_t w38 = SIG1(w36) + w31 + SIG0(w23) + w22; \
        uint32_t w39 = SIG1(w37) + w32 + SIG0(w24) + w23; \
        uint32_t w40 = SIG1(w38) + w33 + SIG0(w25) + w24; \
        uint32_t w41 = SIG1(w39) + w34 + SIG0(w26) + w25; \
        uint32_t w42 = SIG1(w40) + w35 + SIG0(w27) + w26; \
        uint32_t w43 = SIG1(w41) + w36 + SIG0(w28) + w27; \
        uint32_t w44 = SIG1(w42) + w37 + SIG0(w29) + w28; \
        uint32_t w45 = SIG1(w43) + w38 + SIG0(w30) + w29; \
        uint32_t w46 = SIG1(w44) + w39 + SIG0(w31) + w30; \
        uint32_t w47 = SIG1(w45) + w40 + SIG0(w32) + w31; \
        uint32_t w48 = SIG1(w46) + w41 + SIG0(w33) + w32; \
        uint32_t w49 = SIG1(w47) + w42 + SIG0(w34) + w33; \
        uint32_t w50 = SIG1(w48) + w43 + SIG0(w35) + w34; \
        uint32_t w51 = SIG1(w49) + w44 + SIG0(w36) + w35; \
        uint32_t w52 = SIG1(w50) + w45 + SIG0(w37) + w36; \
        uint32_t w53 = SIG1(w51) + w46 + SIG0(w38) + w37; \
        uint32_t w54 = SIG1(w52) + w47 + SIG0(w39) + w38; \
        uint32_t w55 = SIG1(w53) + w48 + SIG0(w40) + w39; \
        uint32_t w56 = SIG1(w54) + w49 + SIG0(w41) + w40; \
        uint32_t w57 = SIG1(w55) + w50 + SIG0(w42) + w41; \
        uint32_t w58 = SIG1(w56) + w51 + SIG0(w43) + w42; \
        uint32_t w59 = SIG1(w57) + w52 + SIG0(w44) + w43; \
        uint32_t w60 = SIG1(w58) + w53 + SIG0(w45) + w44; \
        uint32_t w61 = SIG1(w59) + w54 + SIG0(w46) + w45; \
        uint32_t w62 = SIG1(w60) + w55 + SIG0(w47) + w46; \
        uint32_t w63 = SIG1(w61) + w56 + SIG0(w48) + w47; \
        \
        uint32_t a = 0x6a09e667u; \
        uint32_t b = 0xbb67ae85u; \
        uint32_t c = 0x3c6ef372u; \
        uint32_t d = 0xa54ff53au; \
        uint32_t e = 0x510e527fu; \
        uint32_t f = 0x9b05688cu; \
        uint32_t g = 0x1f83d9abu; \
        uint32_t h = 0x5be0cd19u; \
        \
        RND(a,b,c,d,e,f,g,h,0x428a2f98u,w0); \
        RND(h,a,b,c,d,e,f,g,0x71374491u,w1); \
        RND(g,h,a,b,c,d,e,f,0xb5c0fbcfu,w2); \
        RND(f,g,h,a,b,c,d,e,0xe9b5dba5u,w3); \
        RND(e,f,g,h,a,b,c,d,0x3956c25bu,w4); \
        RND(d,e,f,g,h,a,b,c,0x59f111f1u,w5); \
        RND(c,d,e,f,g,h,a,b,0x923f82a4u,w6); \
        RND(b,c,d,e,f,g,h,a,0xab1c5ed5u,w7); \
        RND(a,b,c,d,e,f,g,h,0xd807aa98u,w8); \
        RND(h,a,b,c,d,e,f,g,0x12835b01u,w9); \
        RND(g,h,a,b,c,d,e,f,0x243185beu,w10); \
        RND(f,g,h,a,b,c,d,e,0x550c7dc3u,w11); \
        RND(e,f,g,h,a,b,c,d,0x72be5d74u,w12); \
        RND(d,e,f,g,h,a,b,c,0x80deb1feu,w13); \
        RND(c,d,e,f,g,h,a,b,0x9bdc06a7u,w14); \
        RND(b,c,d,e,f,g,h,a,0xc19bf174u,w15); \
        RND(a,b,c,d,e,f,g,h,0xe49b69c1u,w16); \
        RND(h,a,b,c,d,e,f,g,0xefbe4786u,w17); \
        RND(g,h,a,b,c,d,e,f,0x0fc19dc6u,w18); \
        RND(f,g,h,a,b,c,d,e,0x240ca1ccu,w19); \
        RND(e,f,g,h,a,b,c,d,0x2de92c6fu,w20); \
        RND(d,e,f,g,h,a,b,c,0x4a7484aau,w21); \
        RND(c,d,e,f,g,h,a,b,0x5cb0a9dcu,w22); \
        RND(b,c,d,e,f,g,h,a,0x76f988dau,w23); \
        RND(a,b,c,d,e,f,g,h,0x983e5152u,w24); \
        RND(h,a,b,c,d,e,f,g,0xa831c66du,w25); \
        RND(g,h,a,b,c,d,e,f,0xb00327c8u,w26); \
        RND(f,g,h,a,b,c,d,e,0xbf597fc7u,w27); \
        RND(e,f,g,h,a,b,c,d,0xc6e00bf3u,w28); \
        RND(d,e,f,g,h,a,b,c,0xd5a79147u,w29); \
        RND(c,d,e,f,g,h,a,b,0x06ca6351u,w30); \
        RND(b,c,d,e,f,g,h,a,0x14292967u,w31); \
        RND(a,b,c,d,e,f,g,h,0x27b70a85u,w32); \
        RND(h,a,b,c,d,e,f,g,0x2e1b2138u,w33); \
        RND(g,h,a,b,c,d,e,f,0x4d2c6dfcu,w34); \
        RND(f,g,h,a,b,c,d,e,0x53380d13u,w35); \
        RND(e,f,g,h,a,b,c,d,0x650a7354u,w36); \
        RND(d,e,f,g,h,a,b,c,0x766a0abbu,w37); \
        RND(c,d,e,f,g,h,a,b,0x81c2c92eu,w38); \
        RND(b,c,d,e,f,g,h,a,0x92722c85u,w39); \
        RND(a,b,c,d,e,f,g,h,0xa2bfe8a1u,w40); \
        RND(h,a,b,c,d,e,f,g,0xa81a664bu,w41); \
        RND(g,h,a,b,c,d,e,f,0xc24b8b70u,w42); \
        RND(f,g,h,a,b,c,d,e,0xc76c51a3u,w43); \
        RND(e,f,g,h,a,b,c,d,0xd192e819u,w44); \
        RND(d,e,f,g,h,a,b,c,0xd6990624u,w45); \
        RND(c,d,e,f,g,h,a,b,0xf40e3585u,w46); \
        RND(b,c,d,e,f,g,h,a,0x106aa070u,w47); \
        RND(a,b,c,d,e,f,g,h,0x19a4c116u,w48); \
        RND(h,a,b,c,d,e,f,g,0x1e376c08u,w49); \
        RND(g,h,a,b,c,d,e,f,0x2748774cu,w50); \
        RND(f,g,h,a,b,c,d,e,0x34b0bcb5u,w51); \
        RND(e,f,g,h,a,b,c,d,0x391c0cb3u,w52); \
        RND(d,e,f,g,h,a,b,c,0x4ed8aa4au,w53); \
        RND(c,d,e,f,g,h,a,b,0x5b9cca4fu,w54); \
        RND(b,c,d,e,f,g,h,a,0x682e6ff3u,w55); \
        RND(a,b,c,d,e,f,g,h,0x748f82eeu,w56); \
        RND(h,a,b,c,d,e,f,g,0x78a5636fu,w57); \
        RND(g,h,a,b,c,d,e,f,0x84c87814u,w58); \
        RND(f,g,h,a,b,c,d,e,0x8cc70208u,w59); \
        RND(e,f,g,h,a,b,c,d,0x90befffau,w60); \
        RND(d,e,f,g,h,a,b,c,0xa4506cebu,w61); \
        RND(c,d,e,f,g,h,a,b,0xbef9a3f7u,w62); \
        RND(b,c,d,e,f,g,h,a,0xc67178f2u,w63); \
        \
        a += 0x6a09e667u; \
        b += 0xbb67ae85u; \
        c += 0x3c6ef372u; \
        d += 0xa54ff53au; \
        e += 0x510e527fu; \
        f += 0x9b05688cu; \
        g += 0x1f83d9abu; \
        h += 0x5be0cd19u; \
        \
        PMIX(0x9E3779B9u, 0x7F4A7C15u); \
        PMIX(0xF39CC060u, 0x106AA070u); \
        PMIX(0xC2B2AE3Du, 0x27D4EB2Fu); \
        PMIX(0x85EBCA77u, 0x165667B1u); \
        \
        (A) = a ^ e ^ rotr32(h, 3); \
        (B) = b + f ^ rotr32(g, 7); \
        (C) = c ^ g + rotr32(f, 13); \
        (D) = d + h ^ rotr32(e, 17); \
    } while(0)

uint32_t hash_a(uint32_t a, uint32_t b, uint32_t c, uint32_t d) {
    uint32_t A,B,C,D;
    HASH(a,b,c,d, A,B,C,D);
    return A;
}
uint32_t hash_b(uint32_t a, uint32_t b, uint32_t c, uint32_t d) {
    uint32_t A,B,C,D;
    HASH(a,b,c,d, A,B,C,D);
    return B;
}
uint32_t hash_c(uint32_t a, uint32_t b, uint32_t c, uint32_t d) {
    uint32_t A,B,C,D;
    HASH(a,b,c,d, A,B,C,D);
    return C;
}
uint32_t hash_d(uint32_t a, uint32_t b, uint32_t c, uint32_t d) {
    uint32_t A,B,C,D;
    HASH(a,b,c,d, A,B,C,D);
    return D;
}


static inline uint32_t lic0(uint32_t len){
    uint32_t m = len * 0x45D9F3Bu;
    uint32_t p1 = LICENCE0 ^ 0xA5A5A5A5u ^ m;
    uint32_t p2 = 0xA5A5A5A5u ^ m;
    return p1 ^ p2;
}
static inline uint32_t lic1(uint32_t len){
    uint32_t m = len * 0x9E3779B9u;
    uint32_t p1 = LICENCE1 + 0x13579BDFu + m;
    uint32_t p2 = 0x13579BDFu + m;
    return p1 - p2;
}
static inline uint32_t lic2(uint32_t len){
    uint32_t m = (len << 16) ^ (len * 0x1B873593u);
    uint32_t p1 = LICENCE2 ^ 0xCAFEBABEu ^ m;
    uint32_t p2 = 0xCAFEBABEu ^ m;
    return p1 ^ p2;
}
static inline uint32_t lic3(uint32_t len){
    uint32_t m = rotr32(len * 0x7FEB352Du, 3);
    uint32_t p1 = LICENCE3 + 0x0F0F0F0Fu + m;
    uint32_t p2 = 0x0F0F0F0Fu + m;
    return p1 - p2;
}

//these functions are useless
static inline uint32_t lic4(uint32_t len){
    uint32_t m = len * 0x27D4EB2Fu;
    uint32_t x = 0x9E3779B9u ^ m;
    x ^= rotr32(x, 11);
    return x;
}

static inline uint32_t lic5(uint32_t len){
    uint32_t m = (len << 7) ^ (len * 0x165667B1u);
    uint32_t x = 0xC2B2AE3Du + m;
    x += rotr32(x, 3);
    return x;
}

//and but obfucated with MBA

uint32_t check(uint32_t ok0, uint32_t aux1, uint32_t ok1, uint32_t ok2,
	uint32_t aux0, uint32_t ok3) {
	return 1763876564 + 2702131896 * ~aux1 + 3236734985 * ~~(aux0 |
		aux1) + 3792662877 * ((ok0 & ok1 | ok0 & ok0) & aux0) +
		1336265316 * (~ok1 & ~aux0 | ok3) + 2100410202 * (ok2 & (ok2
		^ aux0 & ok1)) + 4057483588 * (ok1 & (aux0 ^ aux0) | ok3) +
		2658566175 * ((ok0 | ok3) & (ok1 | ok0) ^ (aux0 ^ aux1 |
		ok1)) + 2336426166 * ((ok0 ^ aux1) & ok1 & ok0 & ok0 & (ok3
		^ ok1)) + 2665678122 * (ok0 & ~ok2 & (~aux0 ^ ok2 & aux1)) +
		4160002560 * ((ok2 | ok2 | ok0 | ok3) ^ (ok3 | ok2) & ok3) +
		2012518912 * ((ok0 & ok0 ^ ok3 & ok3) & ((ok2 | ok3) ^ ok1))
		+ 2124444450 * ok0 + 556298327 * ~((ok2 | ok2) & aux0 &
		aux0) + 2928214731 * (ok2 & ok2 & (aux0 ^ ok1) ^ aux0) +
		1880128009 * ~(aux0 & (aux0 | ok3)) + 2109014628 * (ok1 |
		ok3 | ok0 | aux0) + 1261475427 * ~ok3 + 522472883 * ok3 +
		457602764 * ((ok1 | ok1) ^ aux0 & ok1 ^ aux0) + 2291198898 *
		(ok1 & (aux1 & aux1 | aux1 ^ aux0)) + 3151918564 * ((ok1 |
		aux1 & ok0) & (ok0 ^ ok2 | ok0)) + 3638936235 * ~(aux1 & ok2
		^ aux0 & aux0) + 2215140916 * ~ok0 + 397549968 * (~ok3 ^
		aux0 | ok1 & ok2 & ok2) + 62467748 * (~ok2 | ~ok2) +
		1116710916 * ((ok0 | ~ok2) & aux1) + 1571655443 * ((ok1 |
		aux0 & ok0) ^ aux1) + 389726951 * ~(ok3 & aux0 ^ aux0 & ok2)
		+ 488670346 * (~aux0 ^ ~(ok2 | ok0)) + 1520796479 * (~(ok1 &
		ok1) ^ aux0) + 4025037823 * (ok3 & (~ok1 | ok0 | ok2)) +
		3777888357 * ~(aux0 & ok2 ^ (aux0 | ok1)) + 3953431180 *
		~(ok3 ^ aux1 ^ ok3) + 3832529462 * (~ok1 & (ok0 ^ ok3) |
		~(ok1 | ok3)) + 1610612736 * (aux1 ^ ~ok3 ^ ok0 ^ ok2) +
		3601432623 * (ok1 & ok1 | aux1 ^ aux1 | (aux0 | aux1) & ok2
		& ok1) + 2147483648 * ((ok0 ^ aux0 ^ ok3 ^ ok2) & ((aux1 |
		aux0) ^ ~ok0)) + 3627487855 * ~(ok1 & ok2 & ok3) +
		2557510028 * (aux0 ^ ~ok2 & aux0 & ok3) + 3342309385 * (ok3
		| aux1) + 257693183 * (~(aux1 ^ ok0) ^ (ok1 | ~ok2)) +
		325974241 * (aux0 ^ ok0 | ok2) + 2899085464 * (ok3 & ok0 &
		~ok0 | ok0 & ok3 ^ ~ok1) + 2336426166 * ((ok0 | ok3) & (ok3
		^ aux1) & ok1) + 259147490 * (ok2 & ok2 ^ (aux1 | ok2) ^
		~(aux1 & ok2)) + 3958264609 * ~(ok0 | ok0 & ok1) +
		1606858328 * (~aux0 ^ (aux1 | ok0) ^ ok1) + 2230813913 *
		(~(aux0 & aux0) ^ (ok1 | ok3) & ok3) + 559911312 * ((ok2 ^
		ok1) & ok2 | ~(ok0 ^ ok2)) + 2147483648 * ((aux1 & ok1 |
		aux1) & (aux0 | ok1 | ok0 ^ ok2)) + 3762454465 * aux1 +
		2708653190 * ((ok2 | aux0) & aux1 ^ ~aux1) + 1600995481 *
		(~ok0 ^ aux0 ^ (ok0 | ok1) ^ ok3 ^ ok0) + 557248031 * (ok0 ^
		ok2 ^ ok2 ^ ok1) + 637754473 * ~~(ok1 ^ ok3) + 1781075972 *
		ok1 + 3686257808 * ((aux0 | ok2) ^ ~aux0 ^ ~aux0 & (ok3 ^
		ok1)) + 124089738 * (aux0 & aux1) + 1324445018 * (ok2 ^ (ok2
		| ok2 | aux0 & ok3)) + 1520531196 * ok2 + 2147483648 * ((ok3
		& ok3 ^ (ok1 | ok0)) & (~aux1 | ~aux0)) + 2241954907 * (ok3
		& aux0 & ok3 ^ (aux1 | ok3) ^ ok1 & ok1) + 126180719 * ~aux0
		+ 3595949345 * (ok0 ^ ok0 & ok0 ^ ~ok1 ^ aux0) + 3827501218
		* (aux0 ^ ok1 | aux1 | ~~aux1) + 603738714 * ~(ok0 | ok0 |
		ok2 & ok1) + 214572291 * (ok1 ^ (ok0 | ~ok2)) + 1065029408 *
		(~ok3 & (ok1 | ok3 | aux0 | ok2)) + 2576576974 * (ok3 ^
		~~aux1) + 434026418 * ~(~ok1 ^ ok2 ^ aux1) + 520034557 *
		(~aux0 & ok1 & ok0 ^ (ok1 | aux0) & aux1 & ok1) + 2176939480
		* ((aux0 | aux1 & ok1) ^ ok0) + 1873231664 * (aux1 & (ok2 ^
		ok1) & ~(ok1 & aux0)) + 1234903998 * (~(ok1 ^ ok3) | ok3) +
		2589945806 * ((ok2 & ok1 | ok2 & aux0) ^ ok1) + 1073741824 *
		(aux1 & (ok2 | aux1) ^ ok2 ^ (ok2 | ok3)) + 1992811040 *
		((ok0 | aux0) & (aux0 | ok1) | ~aux1 | aux1) + 1328535155 *
		~(~aux1 ^ ~ok1) + 2284609640 * (~(ok1 ^ ok1) ^ (aux1 ^ aux0
		| ok1 | ok2)) + 1632097282 * (~(ok2 & ok1) | ok2 ^ ok0 ^ ok1
		^ aux1) + 1135125586 * (ok1 & ~ok3 & aux0) + 346333683 *
		~((ok2 ^ aux1) & (aux0 ^ ok2)) + 3221225472 * ~((aux1 | ok3)
		^ ok1 ^ ok0) + 1629541504 * (ok2 | aux1 | ~(ok2 ^ ok2)) +
		2165213786 * (aux1 ^ ok1 ^ ok0 ^ (aux0 ^ ok0 | aux1 &
		ok0));
}



int main(void) {
    /*
    uint32_t a0 = getKeya();
    uint32_t b0 = getKeyb();
    uint32_t c0 = getKeyc();
    uint32_t d0 = getKeyd();
    uint32_t len = getLen();
    */
    char input[33];    
    if (scanf("%32s", input) != 1) {
        return 1;
    }

    uint32_t a0 = conv_a(input);
    uint32_t b0 = conv_b(input);
    uint32_t c0 = conv_c(input);
    uint32_t d0 = conv_d(input);

    uint32_t len = 0;
    while (input[len] != 0) { len++; }


    printf("ok1");
    uint32_t a1 = a0 ^ (0xA5A5A5A5u + len * 0x9E3779B9u);
    uint32_t b1 = b0 + (0x3C6EF372u ^ (len * 0x85EBCA77u));
    uint32_t c1 = c0 ^ (0x1F83D9ABu + (len << 16) + len);
    uint32_t d1 = d0 + (0x5BE0CD19u ^ rotr32(len, 5));

    uint32_t tA = 0xA5A5A5A5u + len * 0x9E3779B9u;
    uint32_t tB = 0x3C6EF372u ^ (len * 0x85EBCA77u);
    uint32_t tC = 0x1F83D9ABu + (len << 16) + len;
    uint32_t tD = 0x5BE0CD19u ^ rotr32(len, 5);

    uint32_t a2 = a0 ^ tA;
    uint32_t b2 = b0 + tB;
    uint32_t c2 = c0 ^ tC;
    uint32_t d2 = d0 + tD;

    uint32_t ha  = hash_a(a1,b1,c1,d1);
    uint32_t hb  = hash_b(a1,b1,c1,d1);
    uint32_t hc  = hash_c(a1,b1,c1,d1);
    uint32_t hd  = hash_d(a1,b1,c1,d1);
    printf("0x%xu 0x%xu 0x%xu 0x%xu\n", ha, hb, hc, hd);

    uint32_t ha2 = hash_a(a2,b2,c2,d2);
    uint32_t hb2 = hash_b(a2,b2,c2,d2);
    uint32_t hc2 = hash_c(a2,b2,c2,d2);
    uint32_t hd2 = hash_d(a2,b2,c2,d2);

    printf("ok2");
    if ((ha != ha2) || (hb != hb2) || (hc != hc2) || (hd != hd2)) return 1;

    uint32_t l0 = lic0(len);
    uint32_t l1 = lic1(len);
    uint32_t l2 = lic2(len);
    uint32_t l3 = lic3(len);
    uint32_t l4 = lic4(len);
    uint32_t l5 = lic5(len);
    
    uint32_t ok0 = (ha ^ rotr32(hb,5)) == (l0 ^ rotr32(l1,5));
    uint32_t ok5 = (l5 + rotr32(l1, 3)) == ((hb ^ d1) + rotr32(hc, 3));
    uint32_t ok1 = (hb + rotr32(hc,7)) == (l1 + rotr32(l2,7));
    uint32_t ok2 = (hc ^ rotr32(hd,11)) == (l2 ^ rotr32(l3,11));
    uint32_t ok4 = (l4 ^ rotr32(l0, 9)) == ((ha + hc) ^ rotr32(hb, 9));
    uint32_t ok3 = (hd + rotr32(ha,13)) == (l3 + rotr32(l0,13));

    uint32_t ok0b = (ha2 ^ rotr32(hb2,5)) == (l0 ^ rotr32(l1,5));
    uint32_t ok5b = (l5 + rotr32(l1, 3)) == ((hb2 ^ d2) + rotr32(hc2, 3));
    uint32_t ok1b = (hb2 + rotr32(hc2,7)) == (l1 + rotr32(l2,7));
    uint32_t ok2b = (hc2 ^ rotr32(hd2,11)) == (l2 ^ rotr32(l3,11));
    uint32_t ok4b = (l4 ^ rotr32(l0, 9)) == ((ha2 + hc2) ^ rotr32(hb2, 9));
    uint32_t ok3b = (hd2 + rotr32(ha2,13)) == (l3 + rotr32(l0,13));


    printf("ok3");
    if ((ok0 != ok0b) | (ok1 != ok1b) | (ok2 != ok2b) | 
        (ok3 != ok3b) | (ok4 != ok4b) | (ok5 != ok5b)) return 1;

    printf("ok\n");
    uint32_t chk1 = check(ok0,  ok5,  ok1,  ok2,  ok4,  ok3);
    uint32_t chk2 = check(ok0b, ok5b, ok1b, ok2b, ok4b, ok3b);
    printf("%d %d\n %d %d %d %d %d %d\n", chk1, chk2, ok0,  ok5,  ok1,  ok2,  ok4,  ok3);
    if (chk1 != chk2) return 1;

    if (chk1) {
        char c1  = 'V' ^ 1;
        char c2  = 'o' ^ 2;
        char c3  = 'u' ^ 3;
        char c4  = 's' ^ 4;
        char c5  = ' ' ^ 5;
        char c6  = 'a' ^ 6;
        char c7  = 'v' ^ 7;
        char c8  = 'e' ^ 8;
        char c9  = 'z' ^ 9;
        char c10 = ' ' ^ 10;
        char c11 = 'g' ^ 11;
        char c12 = 'a' ^ 12;
        char c13 = 'g' ^ 13;
        char c14 = 'n' ^ 14;
        char c15 = 'e' ^ 15;
        char c16 = '.' ^ 16;
        char c17 = '\n' ^ 17;

        printf("%c%c%c%c%c%c%c%c%c%c%c%c%c%c%c%c%c",
            c1 ^ 1,c2 ^ 2,c3 ^ 3,c4 ^ 4,c5 ^ 5,c6 ^ 6,c7 ^ 7,
            c8 ^ 8,c9 ^ 9,c10 ^ 10,c11 ^ 11,c12 ^ 12,c13 ^ 13,c14 ^ 14,c15 ^ 15,c16 ^ 16,c17 ^ 17
        );
        return 0;
    }
    return 1;
}
