#include <stdlib.h>

#include "debug.h"


void *malloc_safe(size_t s) {
    void *obj = malloc(s);
    check_mem(obj);
    return obj;

    error:
        return NULL;
}


void free_safe(void *obj) {
    if (obj != NULL) {
        free(obj);
    }
}
