#ifndef __tree__
#define __tree__

#include <stdbool.h>
#include <stdlib.h>

#define RED true
#define BLACK false


typedef struct treenode {
    char *key;
    void *value;
    char key_size;
    size_t value_size;
    struct treenode *parent;
    struct treenode *left;
    struct treenode *right;
    bool color;
} TreeNode;


typedef struct rbtree {
    TreeNode *root;
    size_t n;
    size_t data_size;
} RBTree;


TreeNode _NIL;
TreeNode *NIL;


int tnode_comp(TreeNode *, TreeNode *);

TreeNode *tnode_create(char *, void *, size_t);

void tnode_destroy(TreeNode *);

void tnode_insert_fixup(RBTree *, TreeNode *);

TreeNode *tnode_leftmost_node(TreeNode *);

void tnode_print(TreeNode *);

void tnode_rotate_left(RBTree *, TreeNode *);

void tnode_rotate_right(RBTree *, TreeNode *);

RBTree *tree_create();

bool tree_delete(RBTree *, char *);

void tree_destroy(RBTree *);

void tree_destroy_helper(TreeNode *);

void tree_insert(RBTree *, char *, void *, size_t);

TreeNode *tree_leftmost_node(RBTree *);

TreeNode *tree_search(char *, RBTree *);

TreeNode *tree_successor_node(TreeNode *);

void tree_traverse_inorder(TreeNode *);

#endif
