#ifndef SEQUOIA_GOST_H
#define SEQUOIA_GOST_H

/*
 * If you read the standard, it belabors the point of copying corresponding
 * bits from point A to point B quite a bit.  It helps to understand that
 * the standard is uniformly little-endian, although it numbers bits from
 * 1 rather than 0, so bit n has value 2^(n-1).  The least significant bit
 * of the 32-bit words that are manipulated in the algorithm is the first,
 * lowest-numbered, in the bit string.
 */

/* A 32-bit data type */
#ifdef __alpha  /* Any other 64-bit machines? */
typedef unsigned int word32;
#else
typedef unsigned long word32;
#endif

extern void kboxinit(void);
extern void gostcrypt(word32 const in[2], word32 out[2], word32 const key[8]);
extern void gostdecrypt(word32 const in[2], word32 out[2], word32 const key[8]);

#endif  // SEQUOIA_GOST_H
