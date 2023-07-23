#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "alloc.h"
#include "api.h"
#include "index.h"
#include "io.h"
#include "sst.h"
#include "tree.h"


int main(int argc, char *argv[]) {
    srand(time(NULL));

    /* test build memtable and write segment file
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
    printf("searching key: %s, found value: %s\n", key, (char *)result->value);

    write_segment_file(tree, "test.db");

    tree_destroy(tree);
    */

    /* test build memtable from segment file
    FILE *fp = fopen("test.db", "r");
    RBTree *memtab = read_sst_segment(fp);
    tree_traverse_inorder(memtab->root);
    tree_destroy(memtab);
    fclose(fp);
    */

    /* test build index from file and search index
    FILE *fp = fopen("test.db", "r");
    Index *index = index_build_from_file(fp);
    char *key = "zebra";
    long start;
    long end;
    index_search(key, index, &start, &end);
    printf("offset of index group for %s: %ld %ld\n", key, start, end);

    if (start != -1) {
        void *data = read_sst_block(fp, start, end);
        TreeNode *found = sst_block_search(key, data, end - start);
        char *value = NULL;
        if (found != NULL) {
            value = malloc(found->value_size);
            memcpy(value, found->value, found->value_size);
            printf("found value for key '%s': %s\n", found->key, value);
        }
        else {
            printf("value not found for key '%s'\n", key);
        }
    }

    fclose(fp);
    index_destroy(index);
    */

    /* test wal read/write
    FILE *wal = fopen("test.wal", "w+");
    write_wal_header(wal);
    write_wal_command(INSERT, "hello", "world", 5, wal);
    write_wal_command(INSERT, "alice", "bob", 3, wal);
    write_wal_command(INSERT, "charlie", "derek", 5, wal);
    write_wal_command(INSERT, "eric", "filip", 5, wal);
    write_wal_command(INSERT, "greg", "hector", 6, wal);
    write_wal_command(INSERT, "charlie", "ida", 3, wal);
    write_wal_command(INSERT, "greg", "juliet", 6, wal);
    write_wal_command(DELETE, "charlie", NULL, 0, wal);
    write_wal_command(INSERT, "charlie", "karl", 4, wal);

    RBTree *memtab = restore_wal(wal);
    printf("restored memtab has %ld nodes\n", memtab->n);
    TreeNode *cur = tree_leftmost_node(memtab);
    if (cur == NULL) {
        printf("rb tree root is null\n");
    }
    else if (cur == NIL) {
        printf("rb tree root is nil\n");
    }
    char value[20];
    while (cur != NIL) {
        if (cur->value != NULL) {
            strncpy(value, cur->value, cur->value_size);
            value[cur->value_size] = '\0';
        }
        else {
            strcpy(value, "null");
        }
        printf("node: key=%s, value=%s\n", cur->key, value);
        cur = tree_successor_node(cur);
    }
    tree_destroy(memtab);
    fclose(wal);
    */


    /* test open db handle, create table, and use table
    Db *db = connect("mykv.db");
    char *key = "metallica";
    use(key, db);
    close(db);
    */

    /* test search table
    Db *db = db_open("mykv.db");
    char *key = "test";
    TreeNode *found = table_get(key, db->master_tb);
    if (found != NULL)
        printf("found table: %s\n", key);
    else
        printf("table not found: %s\n", key);
    db_close(db);
    */

    /* test use table
    Db *db = connect("mykv.db");
    use("users", db);
    close(db);
    */

    /* test put values in user table
    Db *db = connect("mykv.db");
    use("users", db);
    put("hello", "kitty", 5, db);
    put("alice", "saglisse", 8, db);
    put("charlie", "watts", 5, db);
    put("derek", "dominoes", 8, db);
    close(db);
    */

    /* test create new user table and add values
    Db *db = connect("mykv.db");
    use("metallica", db);
    put("james", "hetfield", 8, db);
    put("kirk", "hammett", 7, db);
    put("robert", "trujillo", 8, db);
    put("lars", "ulrich", 6, db);
    close(db);
    */

    /* test search values in user table
    Db *db = connect("mykv.db");
    use("metallica", db);
    char *keys[4] = {"hello", "james", "kirk", "dude"};
    char *key;
    char *value;
    for (int i = 0; i < 4; i++) {
        key = keys[i];
        TreeNode *result = get(key, db);
        if (result != NULL) {
            value = malloc(result->value_size + 1);
            memcpy(value, result->value, result->value_size);
            value[(int)result->value_size] = '\0';
            printf("value for key %s: '%s'\n", key, value);
            free_safe(value);
        }
        else {
            printf("key %s not found\n", key);
        }
    }
    close(db);
    */

    /* test list append left
    List *lst = list_create();
    char *value1 = malloc_safe(6);
    strcpy(value1, "hello");
    char *value2 = malloc_safe(6);
    strcpy(value2, "world");
    list_append_left(lst, value1);
    assert(strcmp((char*)lst->head->data, "hello") == 0);
    assert(strcmp((char*)lst->tail->data, "hello") == 0);
    list_append_left(lst, value2);
    assert(strcmp((char*)lst->head->data, "world") == 0);
    assert(strcmp((char*)lst->head->next->data, "hello") == 0);
    assert(strcmp((char*)lst->tail->data, "hello") == 0);
    list_destroy(lst);
    */

    /* Test restore WAL.
     * First, we add record and not close the connection.
    Db *db = connect("mykv.db");
    use("users", db);
    put("hello", "kitty", 5, db);
    put("alice", "saglisse", 8, db);
    put("charlie", "watts", 5, db);
    put("derek", "dominoes", 8, db);
    */

    /* Then, we connect and check all records are saved.
    Db *db = connect("mykv.db");
    use("users", db);
    char *keys[4] = {"hello", "alice", "charlie", "derek"};
    char *key;
    char *value;
    for (int i = 0; i < 4; i++) {
        key = keys[i];
        TreeNode *result = get(key, db);
        if (result != NULL) {
            value = malloc(result->value_size + 1);
            memcpy(value, result->value, result->value_size);
            value[(int)result->value_size] = '\0';
            printf("value for key %s: '%s'\n", key, value);
            free_safe(value);
        }
        else {
            printf("key %s not found\n", key);
        }
    }
    close(db);
    */

    /*
    Db *db = connect("mykv.db");
    use("metallica", db);
    put("dave", "mustaine", 8, db);
    put("cliff", "burton", 6, db);

    Db *db = db_open("mykv.db");
    use("users", db);
    put("hello", "kitty", 5, db);
    put("alice", "saglisse", 8, db);
    put("charlie", "watts", 5, db);
    put("derek", "dominoes", 8, db);
    close(db);
    */

    /*
    Db *db = connect("mykv.db");
    use("metallica", db);
    put("bob", "rock", 4, db);
    char *keys[4] = {"hello", "bob", "cliff", "dude"};
    char *key;
    char *value;
    for (int i = 0; i < 4; i++) {
        key = keys[i];
        TreeNode *result = db_get(key, db);
        if (result != NULL) {
            value = malloc(result->value_size + 1);
            memcpy(value, result->value, result->value_size);
            value[(int)result->value_size] = '\0';
            printf("value for key %s: '%s'\n", key, value);
            free_safe(value);
        }
        else {
            printf("key %s not found\n", key);
        }
    }
    db_close(db);
    */

    /* measure write performance (this takes approx. 1 sec)
    Db *db = connect("mykv.db");
    use("users", db);
    char *k;
    char *v;
    for (int i = 0; i < 34000; i++) {
        k = random_string(20);
        v = random_string(1000);
        put(k, v, 1000, db);
        free_safe(k);
        free_safe(v);
    }
    close(db);
    */

    return 0;
}
