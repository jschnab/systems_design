#include <stdio.h>
#include <stdlib.h>

#include "debug.h"


void *calloc_safe(size_t nmemb, size_t s) {
    void *obj = calloc(nmemb, s);
    check_mem(obj);
    return obj;

    error:
        fprintf(stderr, "error: can't allocate memory.");
        exit(1);
}



void *malloc_safe(size_t s) {
    void *obj = malloc(s);
    check_mem(obj);
    return obj;

    error:
        fprintf(stderr, "error: can't allocate memory.");
        exit(1);
}


void free_safe(void *obj) {
    if (obj != NULL) {
        free(obj);
    }
}
