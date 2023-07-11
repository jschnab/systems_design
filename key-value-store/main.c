#include <stdint.h>
#include <stdio.h>

#include "index.h"
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

    char *key = "greg";
    TreeNode *result = tree_search(key, tree);
    printf("searching %s, found %s\n", key, (char *)result->value);

    write_segment_file(tree, "test.db");

    tree_destroy(tree);

    FILE *fp = fopen("test.db", "r");
    Index *index = index_build_from_file(fp);
    key = "alice";
    long offset = index_search(key, index);
    printf("offset for %s: %ld\n", key, offset);
    index_destroy(index);

    return 0;
}
