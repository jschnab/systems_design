#ifndef __hashset__
#define __hashset__


#include <stdbool.h>


typedef struct hashset {
    int base_size;
    int size;
    int count;
    char **items;
} HashSet;


char *HS_DELETED_ITEM;


void hs_add(HashSet *, char *);

void hs_destroy(HashSet *);

unsigned int hs_get_hash(char *, int, int);

unsigned int hs_hash(char *, int, int);

HashSet *hs_init();

HashSet *hs_init_sized(int);

int hs_is_prime(int);

int hs_next_prime(int);

void hs_resize(HashSet *, int);

void hs_resize_down(HashSet *);

void hs_resize_up(HashSet *);

bool hs_search(HashSet *, char *value);


#endif
