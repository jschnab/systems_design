#ifndef __alloc__
#define __alloc__


#include <stddef.h>


void *calloc_safe(size_t, size_t);

void *malloc_safe(size_t);

void free_safe(void *);


#endif
