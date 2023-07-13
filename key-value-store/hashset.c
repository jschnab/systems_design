#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "alloc.h"
#include "hashset.h"


static const int HS_PRIME_1 = 151;
static const int HS_PRIME_2 = 163;
static const int HS_BASE_SIZE = 50;


/* Add a value to a HashSet. */
void hs_add(HashSet *set, char *value) {
    /* Eventually resize HashSet. */
    int load = set->count * 100 / set->size;
    if (load > 70) {
        hs_resize_up(set);
    }

    unsigned int index = hs_get_hash(value, set->size, 0);
    char *cur = set->items[index];
    int attempt = 1;
    while (cur != NULL && cur != HS_DELETED_ITEM) {
        /* Do nothing if value already in set. */
        if (strcmp(cur, value) == 0) {
            return;
        }
        index = hs_get_hash(cur, set->size, attempt);
        cur = set->items[index];
        attempt++;
    }
    printf("put item at index %d\n", index);
    set->items[index] = value;
    set->count++;
}


/* Destroy a HashSet. */
void hs_destroy(HashSet *set) {
    free_safe(set->items);
    free_safe(set);
}


/* Discard a value from the set. */
void hs_discard(HashSet *set, char *value) {
    /* Eventually resize HashSet. */
    int load = set->count / set->size * 100;
    if (load < 20) {
        hs_resize_down(set);
    }

    int index = hs_get_hash(value, set->size, 0);
    char *item = set->items[index];
    int attempt = 1;
    while (item != NULL) {
        if (item != HS_DELETED_ITEM) {
            if (strcmp(item, value) == 0) {
                set->items[index] = HS_DELETED_ITEM;
            }
        }
        index = hs_get_hash(value, set->size, attempt);
        item = set->items[index];
        attempt++;
    }
    set->count--;
}


unsigned int hs_get_hash(char *value, int size, int attempt) {
    unsigned int hash_a = hs_hash(value, HS_PRIME_1, size);
    printf("hash_a = %d\n", hash_a);
    unsigned int hash_b = hs_hash(value, HS_PRIME_2, size);
    printf("hash_b = %d\n", hash_b);
    return (unsigned int) (hash_a + (attempt * (hash_b + 1))) % size;
}


unsigned int hs_hash(char *value, int prime, int size) {
    unsigned long hash = 0;
    int len = strlen(value);
    for (int i = 0; i < len; i++) {
        hash += (unsigned long) pow(prime, len - i - 1) * value[i];
        printf("intermediate hash = %ld\n", hash);
    }
    hash %= size;
    return (unsigned int) hash;
}


/* Create an empty HashSet. */
HashSet *hs_init() {
    return hs_init_sized(HS_BASE_SIZE);
}


/* Helper function to initialize a HashSet with at least a certain size. */
HashSet *hs_init_sized(int base_size) {
    HashSet *set = (HashSet *) malloc_safe(sizeof(HashSet));
    set->base_size = base_size;
    set->size = hs_next_prime(set->base_size);
    set->count = 0;
    set->items = calloc_safe((size_t) set->size, sizeof(char *));
    return set;
}


/* Returns whether x is a prime number of not:
 *  1 - prime
 *  0 - not prime
 * -1 - undefined (i.e. x < 2) */
int hs_is_prime(int x) {
    if (x < 2) { return -1; }
    if (x < 4) { return 1; }
    if (x % 2 == 0) { return 0; }
    for (int i = 3; i <= floor(sqrt((double)x)); i+= 2) {
        if (x % i == 0) {
            return 0;
        }
    }
    return 1;
}


/* Returns the next prime number after x, or x if x is prime. */
int hs_next_prime(int x) {
    while (hs_is_prime(x) != 1) {
        x++;
    }
    return x;
}


/* Resize the HashSet when it's growing too large or shrinking too small. */
void hs_resize(HashSet *set, int base_size) {
    if (base_size < HS_BASE_SIZE) {
        return;
    }

    /* Create new set with larger size and copy items in new set. */
    HashSet *new_set = hs_init_sized(base_size);
    for (int i = 0; i < set->size; i++) {
        char *item = set->items[i];
        if (item != NULL && item != HS_DELETED_ITEM) {
            hs_add(new_set, item);
        }
    }

    /* Copy old set attributes to new set. */
    set->base_size = new_set->base_size;
    set->count = new_set->count;

    /* Swap sizes. */
    int tmp_size = set->size;
    set->size = new_set->size;
    new_set->size = tmp_size;

    /* Swap items. */
    char **tmp_items = set->items;
    set->items = new_set->items;
    new_set->items = tmp_items;

    hs_destroy(new_set);
}


/* Convenience function to shrink HashSet. */
void hs_resize_down(HashSet *set) {
    int new_size = set->base_size / 2;
    hs_resize(set, new_size);
}


/* Convenience function to grow a HashSet. */
void hs_resize_up(HashSet *set) {
    int new_size = set->base_size * 2;
    hs_resize(set, new_size);
}


/* Lookup a value in a HashSet and returns:
 * true  - the value is in the set
 * false - the value is not in the set */
bool hs_search(HashSet *set, char *value) {
    unsigned int index = hs_get_hash(value, set->size, 0);
    char *item = set->items[index];
    int attempt = 1;
    while (item != NULL) {
        if (item != HS_DELETED_ITEM) {
            if (strcmp(item, value) == 0) {
                return true;
            }
        }
        index = hs_get_hash(value, set->size, attempt);
        item = set->items[index];
        attempt++;
    }
    return false;
}
