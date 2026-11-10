#include <string.h>

static int row_mode = 0;
static int row_args(int argc, char **argv)
{
    int out = 1;
    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--rows") == 0) row_mode = 1;
        else argv[out++] = argv[i];
    }
    argv[out] = NULL;
    return out;
}
