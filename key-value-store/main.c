#include <stdio.h>

#include "io.h"
#include "tree.h"


int main(int argc, char *argv[]) {
    RBTree *tree = tree_create();

    tree_insert(tree, "hello", "world", 5);
    tree_insert(tree, "alice", "bob", 3);
    tree_insert(tree, "charlie", "derek", 5);
    tree_insert(tree, "eric", "filip", 5);
    tree_insert(tree, "greg", "hector", 6);
    tree_insert(tree, "charlie", "ida", 3);
    tree_insert(tree, "greg", "juliet", 6);
    tree_delete(tree, "charlie");
    tree_insert(tree, "charlie", "karl", 4);

    write_segment_file(tree, "test.db");

    tree_destroy(tree);

    return 0;
}
