#include <limits.h>
#include "media.h"

void mix_channels(char* in_out_a, char* in_b, int length)
{
    short sample_a = 0;
    short sample_b = 0;
    short sample_c = 0;

    int i = 0;
    for (i = 0; i < length; i+= 2)
    {
        sample_a = (short)((in_out_a[i] << 8) | in_out_a[i+1]);
        sample_b = (short)((in_b[i] << 8) | in_b[i+1]);

        sample_c =
            (sample_a < 0 && sample_b < 0)
            ? (sample_a + sample_b) - ((sample_a * sample_b) / SHRT_MIN)
            : (
                (sample_a > 0 && sample_b > 0)
                ? (sample_a + sample_b) - ((sample_a * sample_b) / SHRT_MAX)
                : (sample_a + sample_b));

        in_out_a[i] = (sample_c >> 8) & 0xFF;
        in_out_a[i+1] = sample_c & 0xFF;
    }
}
