#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "debug.h"
#include "alloc.h"
#include "tree.h"


TreeNode _NIL = {NULL, NULL, 0, 0, NULL, NULL, NULL, BLACK};
TreeNode *NIL = &_NIL;


int tnode_comp(TreeNode *a, TreeNode *b) {
    return strcmp(a->key, b->key);
}


/* Parameter 'key' should be null-terminated. */
TreeNode *tnode_create(char *key, void *value, size_t value_size) {
    TreeNode *new = (TreeNode *) malloc_safe(sizeof(TreeNode));
    char key_size = strlen(key);
    new->key = (char *) malloc_safe(key_size + 1);
    new->value = malloc_safe(value_size);
    strcpy(new->key, key);
    memcpy(new->value, value, value_size);
    new->key_size = key_size;
    new->value_size = value_size;
    new->parent = NULL;
    new->left = NULL;
    new->right = NULL;
    return new;
}


void tnode_destroy(TreeNode *node) {
    if (node != NULL && node != NIL) {
        free_safe(node->value);
        free_safe(node);
    }
}


void tnode_insert_fixup(RBTree *tree, TreeNode *z) {
    TreeNode *y;
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
                    tnode_rotate_left(tree, z);
                }
                z->parent->color = BLACK;
                z->parent->parent->color = RED;
                tnode_rotate_right(tree, z->parent->parent);
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
                    tnode_rotate_right(tree, z);
                }
                z->parent->color = BLACK;
                z->parent->parent->color = RED;
                tnode_rotate_left(tree, z->parent->parent);
            }
        }
    }
    tree->root->color = BLACK;
}


TreeNode *tnode_init() {
    return (TreeNode *) malloc_safe(sizeof(TreeNode));

}


TreeNode *tnode_leftmost_node(TreeNode *node) {
    while (node != NIL && node->left != NIL) {
        node = node->left;
    }
    return node;
}


void tnode_print(TreeNode *node) {
    printf(
        "Key=%s, Value=%s, Color=%s, Left=%s, Right=%s, Parent=%s\n",
        node->key,
        (char *) node->value,
        node->color == RED ? "red" : "black",
        node->left != NIL ? node->left->key : "NIL",
        node->right != NIL ? node->right->key : "NIL",
        node->parent != NIL ? node->parent->key : "NIL"
    );
}


/*

     y                      x
    / \    rotate left     / \
   x   c   <-----------   a   y
  / \      ----------->      / \
 a   b     rotate right     b   c

*/
void tnode_rotate_left(RBTree *tree, TreeNode *x) {
    TreeNode *y = x->right;
    x->right = y->left;
    if (y->left != NIL) {
        y->left->parent = x;
    }
    y->parent = x->parent;
    if (x->parent == NIL) {
        tree->root = y;
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


void tnode_rotate_right(RBTree *tree, TreeNode *y) {
    TreeNode *x = y->left;
    y->left = x->right;
    if (x->right != NIL) {
        x->right->parent = y;
    }
    x->parent = y->parent;
    if (x->parent == NIL) {
        tree->root = x;
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


RBTree *tree_create() {
    RBTree *new = (RBTree *) malloc_safe(sizeof(RBTree));
    new->root = NIL;
    new->n = 0;
    new->data_size = 0;
    return new;
}


bool tree_delete(RBTree *tree, char *key) {
    TreeNode *cur = tree->root;
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
            tree->n--;
            tree->data_size -= cur->key_size + cur->value_size;
            free_safe(cur->value);
            cur->value = NULL;
            cur->value_size = 0;
            return true;
        }
    }
    return false;
}


void tree_destroy(RBTree *tree) {
    if (tree->root != NIL) {
        tree_destroy_helper(tree->root);
    }
}


void tree_destroy_helper(TreeNode *node) {
    if (node->left != NIL) {
        tree_destroy_helper(node->left);
    }
    if (node->right != NIL) {
        tree_destroy_helper(node->right);
    }
    tnode_destroy(node);
}


/* Parameter 'key' should be null-terminated. */
void tree_insert(RBTree *tree, char *key, void *value, size_t value_size) {
    TreeNode *par = NIL;
    TreeNode *cur = tree->root;
    int cmp;
    while (cur != NIL) {
        par = cur;
        cmp = strcmp(key, cur->key);

        /* We update a record. */
        if (cmp == 0) {

            /* We resurect a previously deleted record. */
            if (cur->value == NULL) {
                tree->n++;
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
    TreeNode *node = tnode_create(key, value, value_size);
    node->parent = par;
    if (par == NIL) {
        tree->root = node;
    }
    else if (tnode_comp(node, par) < 0) {
        par->left = node;
    }
    else {
        par->right = node;
    }
    node->left = NIL;
    node->right = NIL;
    node->color = RED;
    tnode_insert_fixup(tree, node);
    tree->n++;
    tree->data_size += node->key_size + node->value_size;
}


TreeNode *tree_leftmost_node(RBTree *tree) {
    TreeNode *node = tree->root;
    while (node != NIL && node->left != NIL) {
        node = node->left;
    }
    return node;
}


TreeNode *tree_search(char *key, RBTree *tree) {
    TreeNode *node = tree->root;
    int cmp;
    while (node != NIL) {
        cmp = strcmp(key, node->key);
        if (cmp == 0) {
            return node->value != NULL ? node : NULL;
        }
        else if (cmp < 0) {
            node = node->left;
        }
        else {
            node = node->right;
        }
    }
    return NULL;
}


TreeNode *tree_successor_node(TreeNode *node) {
    if (node == NIL) {
        return NIL;
    }
    if (node->right != NIL) {
        return tnode_leftmost_node(node->right);
    }
    TreeNode *par = node->parent;
    while (par != NIL && node == par->right) {
        par = par->parent;
        node = node->parent;
    }
    return par;
}


void tree_traverse_inorder(TreeNode *node) {
    if (node->left != NIL) {
        tree_traverse_inorder(node->left);
    }
    tnode_print(node);
    if (node->right != NIL) {
        tree_traverse_inorder(node->right);
    }
}
