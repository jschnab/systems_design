#ifndef __api__
#define __api__


#include <stdio.h>

#include "io.h"
#include "namespace.h"


#define MASTER_NS_NAME "master"
#define MASTER_WAL_PATH "master.wal"

/* Root file offsets. */
#define SEG_NUM_OFF VER_SZ
#define SEG_NUM_SZ 8
#define SEG_LST_OFF (SEG_NUM_OFF + SEG_NUM_SZ)
#define SEG_PATH_LEN_SZ 1


typedef struct db {
    char *path;
    FILE *fp;
    Namespace *user_ns;
    Namespace *master_ns;
} Db;


void create_namespace(char *, Db *);

Db *db_open(char *);

void db_close(Db *);


#endif
