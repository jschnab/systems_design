#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "alloc.h"
#include "memtab.h"


Record _NIL = {NULL, NULL, 0, 0, NULL, NULL, NULL, BLACK};
Record *NIL = &_NIL;
static char *RBT_DELETED_ITEM = "TOMBSTONE";


int record_comp(Record *a, Record *b) {
    return strcmp(a->key, b->key);
}


/* Parameter 'key' should be null-terminated.
 * If parameter 'value_size' is 0, the value member will be set to NULL. If
 * 'value_size' is positive, the value member will be allocated. */
Record *record_create(char *key, void *value, size_t value_size) {
    Record *new = (Record *) malloc_safe(sizeof(Record));
    char key_size = strlen(key);
    new->key = (char *) malloc_safe(key_size + 1);
    strcpy(new->key, key);
    new->value = NULL;
    if (value_size > 0) {
        new->value = malloc_safe(value_size);
        memcpy(new->value, value, value_size);
    }
    new->key_size = key_size;
    new->value_size = value_size;
    new->parent = NULL;
    new->left = NULL;
    new->right = NULL;
    return new;
}


void record_destroy(Record *record) {
    if (record != NULL && record != NIL) {
        free_safe(record->value);
        free_safe(record);
    }
}


void record_insert_fixup(Memtable *memtab, Record *z) {
    Record *y;
    while (z->parent->color == RED) {
        if (z->parent == z->parent->parent->left) {
            y = z->parent->parent->right;
            if (y->color == RED) {
                z->parent->color = BLACK;
                y->color = BLACK;
                z->parent->parent->color = RED;
                z = z->parent->parent;
            }
            else {
                if (z == z->parent->right) {
                    z = z->parent;
                    record_rotate_left(memtab, z);
                }
                z->parent->color = BLACK;
                z->parent->parent->color = RED;
                record_rotate_right(memtab, z->parent->parent);
            }
        }
        else {
            y = z->parent->parent->left;
            if (y->color == RED) {
                z->parent->color = BLACK;
                y->color = BLACK;
                z->parent->parent->color = RED;
                z = z->parent->parent;
            }
            else {
                if (z == z->parent->left) {
                    z = z->parent;
                    record_rotate_right(memtab, z);
                }
                z->parent->color = BLACK;
                z->parent->parent->color = RED;
                record_rotate_left(memtab, z->parent->parent);
            }
        }
    }
    memtab->root->color = BLACK;
}


Record *record_init() {
    return (Record *) malloc_safe(sizeof(Record));

}


Record *record_leftmost(Record *record) {
    while (record != NIL && record->left != NIL) {
        record = record->left;
    }
    return record;
}


/* This function should accept an argument that is a pointer to a function to
 * serialize the value. */
void record_print(Record *record) {
    printf(
        "Key=%s, Value=%s, Color=%s, Left=%s, Right=%s, Parent=%s\n",
        record->key,
        (char *) record->value,
        record->color == RED ? "red" : "black",
        record->left != NIL ? record->left->key : "NIL",
        record->right != NIL ? record->right->key : "NIL",
        record->parent != NIL ? record->parent->key : "NIL"
    );
}


/*

     y                      x
    / \    rotate left     / \
   x   c   <-----------   a   y
  / \      ----------->      / \
 a   b     rotate right     b   c

*/
void record_rotate_left(Memtable *memtab, Record *x) {
    Record *y = x->right;
    x->right = y->left;
    if (y->left != NIL) {
        y->left->parent = x;
    }
    y->parent = x->parent;
    if (x->parent == NIL) {
        memtab->root = y;
    }
    else if (x == x->parent->left) {
        x->parent->left = y;
    }
    else {
        x->parent->right = y;
    }
    y->left = x;
    x->parent = y;
}


void record_rotate_right(Memtable *memtab, Record *y) {
    Record *x = y->left;
    y->left = x->right;
    if (x->right != NIL) {
        x->right->parent = y;
    }
    x->parent = y->parent;
    if (x->parent == NIL) {
        memtab->root = x;
    }
    else if (y == y->parent->right) {
        y->parent->right = x;
    }
    else {
        y->parent->left = x;
    }
    x->right = y;
    y->parent = x;
}


Memtable *memtable_create() {
    Memtable *new = (Memtable *) malloc_safe(sizeof(Memtable));
    new->root = NIL;
    new->n = 0;
    new->data_size = 0;
    return new;
}


bool memtable_delete(Memtable *memtab, char *key) {
    Record *cur = memtab->root;
    int cmp;
    while (cur != NIL) {
        cmp = strcmp(key, cur->key);
        if (cmp < 0) {
            cur = cur->left;
        }
        else if (cmp > 0) {
            cur = cur->right;
        }
        else {
            memtab->n--;
            memtab->data_size -= cur->key_size + cur->value_size;
            free_safe(cur->value);
            cur->value = RBT_DELETED_ITEM;
            cur->value_size = 0;
            return true;
        }
    }
    return false;
}


void memtable_destroy(Memtable *memtab) {
    if (memtab->root != NIL) {
        memtable_destroy_helper(memtab->root);
    }
}


void memtable_destroy_helper(Record *record) {
    if (record->left != NIL) {
        memtable_destroy_helper(record->left);
    }
    if (record->right != NIL) {
        memtable_destroy_helper(record->right);
    }
    record_destroy(record);
}


/* Parameter 'key' should be null-terminated. */
void memtable_insert(Memtable *memtab, char *key, void *value, size_t value_size) {
    Record *par = NIL;
    Record *cur = memtab->root;
    int cmp;
    while (cur != NIL) {
        par = cur;
        cmp = strcmp(key, cur->key);

        /* We update a record. */
        if (cmp == 0) {

            /* We resurect a previously deleted record. */
            if (cur->value == NULL) {
                memtab->n++;
            }

            /* Old and new value sizes do not match, we re-allocate the value. */
            if (value_size != cur->value_size) {
                free_safe(cur->value);
                cur->value = malloc_safe(value_size);
                cur->value_size = value_size;
            }

            memcpy(cur->value, value, value_size);
            return;
        }
        else if (cmp < 0) {
            cur = cur->left;
        }
        else {
            cur = cur->right;
        }
    }
    Record *record = record_create(key, value, value_size);
    record->parent = par;
    if (par == NIL) {
        memtab->root = record;
    }
    else if (record_comp(record, par) < 0) {
        par->left = record;
    }
    else {
        par->right = record;
    }
    record->left = NIL;
    record->right = NIL;
    record->color = RED;
    record_insert_fixup(memtab, record);
    memtab->n++;
    memtab->data_size += record->key_size + record->value_size;
}


Record *memtable_leftmost_record(Memtable *memtab) {
    Record *record = memtab->root;
    while (record != NIL && record->left != NIL) {
        record = record->left;
    }
    return record;
}


Record *memtable_search(char *key, Memtable *memtab) {
    Record *record = memtab->root;
    int cmp;
    while (record != NIL) {
        cmp = strcmp(key, record->key);
        if (cmp == 0) {
            if (record->value == RBT_DELETED_ITEM) {
                return NULL;
            }
            else {
                return record;
            }
        }
        else if (cmp < 0) {
            record = record->left;
        }
        else {
            record = record->right;
        }
    }
    return NULL;
}


Record *memtable_successor_record(Record *record) {
    if (record == NIL) {
        return NIL;
    }
    if (record->right != NIL) {
        return record_leftmost(record->right);
    }
    Record *par = record->parent;
    while (par != NIL && record == par->right) {
        par = par->parent;
        record = record->parent;
    }
    return par;
}


void memtable_traverse_inorder(Record *record) {
    if (record->left != NIL) {
        memtable_traverse_inorder(record->left);
    }
    record_print(record);
    if (record->right != NIL) {
        memtable_traverse_inorder(record->right);
    }
}
